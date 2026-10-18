"""Contrôle quotidien des valeurs publiées, sans modifier les observations.

Après la collecte : python -m src.daily_audit --publish
Compare Supabase à sa provenance publiée et recalcule DVF depuis les CSV.
Les contrôles vérifient la cohérence technique, pas l'exhaustivité des sources.
"""
import argparse
import json
import math
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from supabase import create_client

from .extract.atmo import get_primary_pollution_value
from .extract.dvf import DATA_DIR, DEFAULT_DVF_YEAR, get_commune_stats
from .main_pipeline import CITIES_TO_PROCESS
from .provenance import PUBLIC_METADATA_BUCKET, publish_metadata, snapshot

ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "data/daily-audit.json"
CATEGORIES = ("sport", "park", "supermarket", "pharmacy", "school", "restaurant", "hospital")


def recent(value, now, days):
    try:
        date = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return date.tzinfo is not None and timedelta(0) <= now - date <= timedelta(days=days)
    except (AttributeError, TypeError, ValueError):
        return False


def equal_number(a, b):
    if a is None or b is None:
        return a is b
    return (isinstance(a, (int, float)) and isinstance(b, (int, float))
            and math.isfinite(a) and math.isfinite(b) and math.isclose(a, b, abs_tol=.005))


def source_warnings(poi, now):
    """Distinguer le jour de l'appel de l'âge de la base du serveur OSM."""
    timestamp = poi.get("source_timestamp")
    if timestamp and not recent(timestamp, now, 7):
        return [f"La base OSM du serveur est datée du {timestamp}, soit plus de sept jours ou une date invalide. Le comptage reflète cet état de la source."]
    if not timestamp:
        return ["Date de la base OSM non renseignée par le serveur."]
    return []


def build_report(rows, provenance, frames, expected=CITIES_TO_PROCESS, now=None):
    """frames : chemins CSV ou DataFrames déjà téléchargés, sans nouvel appel d'API."""
    now = now or datetime.now(timezone.utc)
    report = {"schema": "daily-audit-v1", "audited_at": now.isoformat(),
              "method": "Comparaison Supabase/provenance publiée et recalcul DVF depuis les CSV départementaux.",
              "cities": {}}
    by_code = {row["insee_code"]: row for row in rows}
    for city in expected:
        code = city["insee"]
        row = by_code.get(code)
        entry = {"city": city["name"], "audited_at": report["audited_at"], "checks": [], "warnings": []}
        report["cities"][code] = entry

        def check(name, valid):
            entry["checks"].append({"name": name, "passed": bool(valid)})

        check("Ville présente dans Supabase", row is not None)
        if row is None:
            entry["status"] = "failed"
            continue
        saved = provenance.get("cities", {}).get(code) or {}
        check("Valeurs identiques à la provenance publiée", saved.get("snapshot") == snapshot(row))
        check("Enregistrement actualisé depuis moins de 24 heures", recent(row.get("updated_at"), now, 1))
        geo = saved.get("geocoding") or {}
        check("Coordonnées rattachées au bon code INSEE", geo.get("insee_code") == code
              and equal_number(geo.get("latitude"), row.get("latitude"))
              and equal_number(geo.get("longitude"), row.get("longitude"))
              and isinstance(row.get("latitude"), (int, float)) and -90 <= row["latitude"] <= 90
              and isinstance(row.get("longitude"), (int, float)) and -180 <= row["longitude"] <= 180)
        risks = saved.get("risks") or {}
        labels = risks.get("risks")
        check("Liste et nombre de risques concordants", risks.get("code_insee") == code
              and isinstance(labels, list) and all(isinstance(s, str) and s for s in labels)
              and len(set(labels)) == len(labels) == risks.get("total_risks") == row.get("risks_count"))
        poi = saved.get("poi_commune") or {}
        counts = poi.get("counts") or {}
        relation = poi.get("relation_id")
        check("Services comptés dans les limites de la commune", poi.get("status") == "available"
              and poi.get("scope") == "commune" and poi.get("insee_code") == code
              and poi.get("method") == "osm-commune-nwr-count-v1"
              and type(relation) is int and relation > 0 and poi.get("area_id") == relation + 3600000000)
        check("Sept comptages de services conformes aux valeurs affichées", set(counts) == set(CATEGORIES)
              and all(type(counts[k]) is int and counts[k] >= 0 and counts[k] == row.get("poi_" + k) for k in counts))
        check("Date des services valide, au plus sept jours", recent(poi.get("collected_at"), now, 7))
        if poi.get("retained"):
            entry["warnings"].append("Collecte OSM précédente conservée avec sa date d'origine.")
        entry["warnings"].extend(source_warnings(poi, now))
        air = saved.get("air") or {}
        pm = (air.get("measurements") or {}).get("pm25") or (air.get("measurements") or {}).get("pm2.5")
        check("Valeur PM2.5 conforme à la mesure et à son unité", equal_number(get_primary_pollution_value(air), row.get("air_quality_score"))
              and (row.get("air_quality_score") is None or pm is not None))
        if row.get("air_quality_score") is not None:
            distance = air.get("distance_km")
            check("Station et date du relevé d'air documentées", bool(air.get("station_id"))
                  and isinstance(distance, (int, float)) and 0 <= distance <= 25
                  and recent(pm.get("measured_at") if pm else None, now, 3))
        else:
            entry["warnings"].append("Aucun relevé PM2.5 exploitable pour cette ville.")
        dvf = saved.get("dvf") or {}
        if city["dept"] in {"57", "67", "68"}:
            check("Absence DVF conforme au périmètre de la source", row.get("avg_price_m2") is None and row.get("total_transactions") is None)
            entry["warnings"].append("Département hors couverture DVF.")
        else:
            frame = frames.get(city["dept"])
            if isinstance(frame, Path):
                frame = pd.read_csv(frame, dtype={"code_commune": str}, low_memory=False)
            stats = get_commune_stats(frame, code, city["name"]) if frame is not None else None
            check("Recalcul DVF depuis le fichier départemental disponible", stats is not None)
            if stats is not None:
                check("Médianes, effectifs et période DVF reproductibles", dvf.get("year") == DEFAULT_DVF_YEAR
                      and all(dvf.get(k) == stats.get(k) for k in ("by_type", "nb_ventes_totales", "period_start", "period_end", "excluded_by_price", "method"))
                      and equal_number(row.get("avg_price_m2"), stats["prix_m2_median_global"])
                      and row.get("total_transactions") == stats["nb_ventes_totales"])
        entry["status"] = "passed" if all(c["passed"] for c in entry["checks"]) else "failed"
        # Seules les métadonnées d'une ligne intégralement contrôlée peuvent servir de repli au site.
        if entry["status"] == "passed":
            entry.update({k: saved[k] for k in ("snapshot", "geocoding", "risks", "air", "poi_commune", "dvf") if k in saved})
    entries = list(report["cities"].values())
    report["summary"] = {"total": len(entries), "passed": sum(e["status"] == "passed" for e in entries),
                         "failed": sum(e["status"] == "failed" for e in entries),
                         "warnings": sum(len(e["warnings"]) for e in entries)}
    report["success"] = bool(entries) and report["summary"]["failed"] == 0
    return report


def run_audit(publish=False, client=None):
    load_dotenv(ROOT / ".env")
    client = client or create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])
    rows = client.table("cities_qol").select("*").execute().data
    # Contrôler le document réellement publié, pas seulement une copie locale.
    provenance = json.loads(client.storage.from_(PUBLIC_METADATA_BUCKET).download("provenance.json"))
    frames = {}
    for city in CITIES_TO_PROCESS:
        dept = city["dept"]
        path = DATA_DIR / f"dvf_{DEFAULT_DVF_YEAR}_{dept}.csv"
        if dept not in frames and path.exists():
            frames[dept] = path
    report = build_report(rows, provenance, frames)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    if publish:
        publish_metadata(client, REPORT_PATH, object_name="audit.json")
    print(json.dumps(report["summary"], ensure_ascii=False))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--publish", action="store_true", help="Publier aussi le rapport dans Supabase Storage")
    args = parser.parse_args()
    raise SystemExit(0 if run_audit(publish=args.publish)["success"] else 1)
