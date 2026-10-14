"""Métadonnées publiques locales liées exactement aux lignes Supabase.

Le schéma distant reste compatible : publier web/ avec le fichier de provenance.
Ne contient ni clés privées ni variables d'environnement.
"""
import json
from pathlib import Path

PUBLIC_DIR = Path(__file__).resolve().parents[1] / "web" / "data"
PUBLIC_METADATA_BUCKET = "qol-public-metadata"
SNAPSHOT_FIELDS = ["updated_at", "latitude", "longitude", "avg_price_m2",
                   "total_transactions", "risks_count", "air_quality_score",
                   "poi_sport", "poi_park", "poi_supermarket", "poi_pharmacy",
                   "poi_school", "poi_restaurant", "poi_hospital"]


def snapshot(row):
    return {field: row.get(field) for field in SNAPSHOT_FIELDS}


def save_metadata(code, row, metadata):
    PUBLIC_DIR.mkdir(parents=True, exist_ok=True)
    path = PUBLIC_DIR / "provenance.json"
    document = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"cities": {}}
    document["cities"][code] = {"snapshot": snapshot(row), **metadata}
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(document, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    temporary.replace(path)


def publish_metadata(client, path=None):
    """Publie uniquement le JSON public, pour synchroniser aussi les sites locaux."""
    path = PUBLIC_DIR / "provenance.json" if path is None else Path(path)
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
        "provenance.json", content,
        file_options={"content-type": "application/json", "cache-control": "60", "upsert": "true"},
    )
"""Métadonnées publiques locales liées exactement aux lignes Supabase.

Le schéma distant reste compatible : publier web/ avec le fichier de provenance.
Ne contient ni clés privées ni variables d'environnement.
"""
import json
from pathlib import Path

PUBLIC_DIR = Path(__file__).resolve().parents[1] / "web" / "data"
SNAPSHOT_FIELDS = ["updated_at", "latitude", "longitude", "avg_price_m2",
                   "total_transactions", "risks_count", "air_quality_score",
                   "poi_sport", "poi_park", "poi_supermarket", "poi_pharmacy",
                   "poi_school", "poi_restaurant", "poi_hospital"]


def snapshot(row):
    return {field: row.get(field) for field in SNAPSHOT_FIELDS}


def save_metadata(code, row, metadata):
    PUBLIC_DIR.mkdir(parents=True, exist_ok=True)
    path = PUBLIC_DIR / "provenance.json"
    document = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"cities": {}}
    document["cities"][code] = {"snapshot": snapshot(row), **metadata}
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(document, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    temporary.replace(path)
