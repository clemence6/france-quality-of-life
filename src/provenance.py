"""Métadonnées publiques locales liées exactement aux lignes Supabase.

Le schéma distant reste compatible : publier web/ avec le fichier de provenance.
Ne contient ni clés privées ni variables d'environnement.
"""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

PUBLIC_DIR = Path(__file__).resolve().parents[1] / "web" / "data"
PUBLIC_METADATA_BUCKET = "qol-public-metadata"
SNAPSHOT_FIELDS = ["updated_at", "latitude", "longitude", "avg_price_m2",
                   "total_transactions", "risks_count", "air_quality_score",
                   "poi_sport", "poi_park", "poi_supermarket", "poi_pharmacy",
                   "poi_school", "poi_restaurant", "poi_hospital"]


def snapshot(row):
    return {field: row.get(field) for field in SNAPSHOT_FIELDS}


def recent_commune_services(paths=None, now=None):
    """Repli sur des comptages communaux contrôlés, âgés de sept jours au maximum."""
    now = now or datetime.now(timezone.utc)
    paths = paths if paths is not None else [PUBLIC_DIR / "audit.json", PUBLIC_DIR / "provenance.json"]
    categories = {"sport", "park", "supermarket", "pharmacy", "school", "restaurant", "hospital"}
    result = {}
    for path in paths:
        try:
            document = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(document, dict) or not isinstance(document.get("cities"), dict):
            continue
        for code, entry in document["cities"].items():
            if not isinstance(entry, dict):
                continue
            poi = entry.get("poi_commune") or {}
            if not isinstance(poi, dict):
                continue
            counts = poi.get("counts") or {}
            if not isinstance(counts, dict):
                continue
            relation, area = poi.get("relation_id"), poi.get("area_id")
            if (poi.get("scope") != "commune" or poi.get("status") != "available"
                    or poi.get("insee_code") != code or poi.get("method") != "osm-commune-nwr-count-v1"
                    or type(relation) is not int or relation <= 0 or area != relation + 3600000000
                    or set(counts) != categories or any(type(v) is not int or v < 0 for v in counts.values())
                    or not any(counts.values())):
                continue
            try:
                collected = datetime.fromisoformat(poi["collected_at"].replace("Z", "+00:00"))
                if collected.tzinfo is None or not timedelta(0) <= now - collected <= timedelta(days=7):
                    continue
            except (KeyError, TypeError, ValueError):
                continue
            if code not in result or collected > datetime.fromisoformat(result[code]["collected_at"].replace("Z", "+00:00")):
                result[code] = poi.copy()
    return result


def save_metadata(code, row, metadata):
    PUBLIC_DIR.mkdir(parents=True, exist_ok=True)
    path = PUBLIC_DIR / "provenance.json"
    document = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"cities": {}}
    document["cities"][code] = {"snapshot": snapshot(row), **metadata}
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(document, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    temporary.replace(path)


def publish_metadata(client, path=None, *, object_name="provenance.json"):
    """Publie uniquement le JSON public, pour synchroniser aussi les sites locaux."""
    path = PUBLIC_DIR / "provenance.json" if path is None else Path(path)
    if object_name not in {"provenance.json", "audit.json"}:
        raise ValueError("Nom de document public invalide")
    content = path.read_bytes()
    document = json.loads(content)
    if not isinstance(document.get("cities"), dict):
        raise ValueError("Document de provenance invalide")
    bucket = next((b for b in client.storage.list_buckets() if b.id == PUBLIC_METADATA_BUCKET), None)
    if bucket is None:
        client.storage.create_bucket(PUBLIC_METADATA_BUCKET, options={
            "public": True, "allowed_mime_types": ["application/json"], "file_size_limit": 2 * 1024 * 1024,
        })
    elif not bucket.public:
        raise RuntimeError("Le bucket de métadonnées existant est privé : configuration à vérifier")
    client.storage.from_(PUBLIC_METADATA_BUCKET).upload(
        object_name, content,
        file_options={"content-type": "application/json", "cache-control": "60", "upsert": "true"},
    )
