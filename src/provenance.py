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
