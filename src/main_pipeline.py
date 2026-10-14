"""
Script principal d'orchestration : extrait, transforme et charge toutes les
sources dans Supabase.

Lancer depuis le dossier src/ :
    cd src
    python main_pipeline.py
"""

import os
import time
import json
from datetime import datetime, timezone
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from provenance import save_metadata, publish_metadata, recent_commune_services
from dotenv import load_dotenv
from supabase import create_client, Client

from extract.ban_geocode import geocode
from extract.georisques import get_risks_by_commune, parse_risks_data
from extract.atmo import get_air_quality_openaq, get_primary_pollution_value
from extract.overpass_osm import get_commune_poi_counts
from extract.dvf import download_dvf_department, get_commune_stats, DEFAULT_DVF_YEAR

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

TABLE_NAME = "cities_qol"
REPORT_PATH = Path(__file__).resolve().parents[1] / "data" / "pipeline-run.json"

CITIES_TO_PROCESS = [
    {"name": "Paris", "dept": "75", "insee": "75056"},
    {"name": "Marseille", "dept": "13", "insee": "13055"},
    {"name": "Lyon", "dept": "69", "insee": "69123"},
    {"name": "Toulouse", "dept": "31", "insee": "31555"},
    {"name": "Nice", "dept": "06", "insee": "06088"},
    {"name": "Nantes", "dept": "44", "insee": "44109"},
    {"name": "Strasbourg", "dept": "67", "insee": "67482"},
    {"name": "Montpellier", "dept": "34", "insee": "34172"},
    {"name": "Bordeaux", "dept": "33", "insee": "33063"},
    {"name": "Lille", "dept": "59", "insee": "59350"},
    {"name": "Toulon", "dept": "83", "insee": "83137"},
]


def run_pipeline(client=None, cities=None, delay=3, report_path=REPORT_PATH):
    """Met à jour la base et renvoie un bilan exploitable par GitHub Actions."""
    if client is None:
        url, key = os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY")
        if not url or not key or not os.getenv("OPENAQ_API_KEY"):
            raise RuntimeError("SUPABASE_URL, SUPABASE_KEY et OPENAQ_API_KEY sont nécessaires.")
        client = create_client(url, key)
    selected_cities = CITIES_TO_PROCESS if cities is None else cities
    report = {"started_at": datetime.now(timezone.utc).isoformat(),
              "requested": len(selected_cities), "updated": [], "failed": [], "source_errors": [],
              "fresh_services": [], "retained_services": []}
    dvf_cache = {}
    previous_services = recent_commune_services()

    for city in selected_cities:
        city_name = city["name"]
        dept = city["dept"]
        fallback_insee = city["insee"]

        print(f"\n{'=' * 40}\n🚀 Traitement : {city_name} (Dept {dept})\n{'=' * 40}")

        try:
            # 1. Géocodage
            print("📍 [1/5] Géocodage...")
            geo_data = geocode(city_name, insee_code=fallback_insee)
            if not geo_data:
                raise ValueError("Géocodage indisponible")

            lat, lon = geo_data.get("latitude"), geo_data.get("longitude")
            postal_code = geo_data.get("postcode")
            insee_code = geo_data["insee_code"]  # code contrôlé par le géocodage
            print(f"   -> INSEE utilisé : {insee_code} | CP : {postal_code} | Lat/Lon : {lat}, {lon}")

            # 2. Géorisques
            print("⚠️  [2/5] Géorisques...")
            try:
                raw_risks = get_risks_by_commune(insee_code)
                risk_summary = parse_risks_data(raw_risks)
                if risk_summary["code_insee"] != insee_code:
                    raise ValueError("Commune absente de GASPAR")
                risks_count = risk_summary["total_risks"]
            except Exception as e:
                print(f"   ⚠️ Géorisques indisponible (donnée manquante) : {e}")
                report["source_errors"].append({"city": city_name, "source": "GASPAR", "error": type(e).__name__})
                risks_count = None
                risk_summary = None
            print(f"   -> {risks_count} risques recensés")

            # 3. Qualité de l'air
            print("💨 [3/5] Qualité de l'air (OpenAQ)...")
            try:
                air_data = get_air_quality_openaq(city_name, latitude=lat, longitude=lon)
                air_quality_score = get_primary_pollution_value(air_data)
            except Exception as e:
                print(f"   ⚠️ Qualité de l'air indisponible : {e}")
                report["source_errors"].append({"city": city_name, "source": "OpenAQ", "error": type(e).__name__})
                air_quality_score = None
                air_data = None
            print(f"   -> valeur retenue : {air_quality_score}")

            # 4. POI OpenStreetMap
            print("🏛️  [4/5] OpenStreetMap (Overpass)...")
            try:
                poi_metadata = get_commune_poi_counts(insee_code, relation_id=previous_services.get(insee_code, {}).get("relation_id"))
                poi_data = poi_metadata["counts"]
                report["fresh_services"].append(city_name)
            except Exception as e:
                print(f"   ⚠️ Overpass indisponible (données manquantes) : {e}")
                cached = previous_services.get(insee_code)
                report["source_errors"].append({"city": city_name, "source": "Overpass", "error": type(e).__name__, "retained": bool(cached)})
                if cached:
                    poi_metadata = {**cached, "retained": True, "refresh_status": "failed",
                                    "last_attempt_at": datetime.now(timezone.utc).isoformat()}
                    poi_data = cached["counts"]
                    report["retained_services"].append({"city": city_name, "collected_at": cached["collected_at"]})
                else:
                    poi_data = {}
                    poi_metadata = {"status": "unavailable", "scope": "commune", "insee_code": insee_code}
            print(f"   -> {poi_data}")

            # 5. DVF (immobilier)
            print("🏠 [5/5] DVF...")
            stats_immo = None
            try:
                # Ces départements ne sont pas couverts par DVF : absence attendue.
                covered = dept not in {"57", "67", "68"}
                if covered and dept not in dvf_cache:
                    dvf_cache[dept] = download_dvf_department(dept, DEFAULT_DVF_YEAR)
                if covered and dvf_cache[dept] is None:
                    raise RuntimeError("Fichier DVF indisponible")
                if covered:
                    stats_immo = get_commune_stats(dvf_cache[dept], insee_code, city_name)
            except Exception as e:
                print(f"   ⚠️ DVF indisponible : {e}")
                report["source_errors"].append({"city": city_name, "source": "DVF", "error": type(e).__name__})
            print(f"   -> {stats_immo}")

            # --- PAYLOAD ---
            payload = {
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "insee_code": insee_code,
                "city_name": city_name,
                "postal_code": postal_code,
                "latitude": lat,
                "longitude": lon,
                "risks_count": risks_count,
                "poi_sport": poi_data.get("sport"),
                "poi_park": poi_data.get("park"),
                "poi_supermarket": poi_data.get("supermarket"),
                "poi_pharmacy": poi_data.get("pharmacy"),
                "poi_school": poi_data.get("school"),
                "poi_restaurant": poi_data.get("restaurant"),
                "poi_hospital": poi_data.get("hospital"),
                "avg_price_m2": stats_immo.get("prix_m2_median_global") if stats_immo else None,
                "total_transactions": stats_immo.get("nb_ventes_totales") if stats_immo else None,
                "air_quality_score": air_quality_score,
            }

            print("☁️  Envoi vers Supabase...")
            result = client.table(TABLE_NAME).upsert(payload, on_conflict="insee_code").execute()
            if not result.data:
                raise RuntimeError("Supabase n’a pas retourné la ligne enregistrée")
            stored_row = result.data[0]
            save_metadata(insee_code, stored_row, {
                "collected_at": payload["updated_at"],
                "geocoding": geo_data,
                "risks": risk_summary,
                "air": air_data,
                "poi_commune": poi_metadata,
                "dvf": {**stats_immo, "year": DEFAULT_DVF_YEAR} if stats_immo else None,
            })
            print(f"✅ {city_name} traitée avec succès (métadonnées dans web/data/provenance.json).")
            report["updated"].append(city_name)

        except Exception as e:
            print(f"❌ Erreur critique lors du traitement de {city_name}: {e}")
            report["failed"].append({"city": city_name, "error": type(e).__name__})
        finally:
            time.sleep(delay)  # ménage les API publiques, y compris après une erreur

    report["metadata_published"] = False
    if report["updated"]:
        try:
            publish_metadata(client)
            report["metadata_published"] = True
        except Exception as e:
            print(f"❌ Publication des métadonnées impossible : {type(e).__name__}")
            report["source_errors"].append({"city": "Métadonnées du site", "source": "Supabase Storage", "error": type(e).__name__})
    report["finished_at"] = datetime.now(timezone.utc).isoformat()
    # Une donnée récente conservée reste datée et signalée dans le bilan et le site.
    unresolved = [error for error in report["source_errors"] if not error.get("retained")]
    report["success"] = bool(selected_cities) and not report["failed"] and not unresolved
    report_path = Path(report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    result = run_pipeline()
    raise SystemExit(0 if result["success"] else 1)
