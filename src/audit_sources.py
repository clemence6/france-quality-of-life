"""Audit reproductible en lecture seule ; aucune écriture dans Supabase.

python -m src.audit_sources
Lit la configuration publique, contrôle IGN/GASPAR pour chaque ville, recalcule
les caches DVF présents, écrit web/data/audit.json et data/source-audit.json.
"""
import json
import re
import argparse
import os
import ssl
import tempfile
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
import requests
from .extract.ban_geocode import geocode
from .extract.georisques import get_risks_by_commune, parse_risks_data
from .extract.dvf import get_commune_stats, DATA_DIR, DEFAULT_DVF_YEAR
from .extract.overpass_osm import get_commune_poi_counts
from .extract.atmo import get_air_quality_openaq, OPENAQ_API_KEY
from .provenance import snapshot, PUBLIC_DIR

ROOT = Path(__file__).resolve().parents[1]
DEPARTMENTS = {"75056": "75", "13055": "13", "69123": "69", "31555": "31",
               "06088": "06", "44109": "44", "67482": "67", "34172": "34",
               "33063": "33", "59350": "59", "83137": "83"}


def run_audit(live=False):
    # requests/certifi peut ignorer le magasin Windows, contrairement à urllib.
    # Conserver la validation TLS et toute configuration utilisateur explicite.
    if os.name == "nt" and not os.environ.get("REQUESTS_CA_BUNDLE"):
        trust = Path(tempfile.gettempdir()) / "habiter-system-trust.pem"
        trust.write_text("".join(ssl.DER_cert_to_PEM_cert(cert)
                                 for cert in ssl.create_default_context().get_ca_certs(binary_form=True)))
        os.environ["REQUESTS_CA_BUNDLE"] = str(trust)
    config = (ROOT / "web/config.js").read_text(encoding="utf-8")
    url = re.search(r'url:\s*"([^"]+)"', config).group(1)
    key = re.search(r'anonKey:\s*"([^"]+)"', config).group(1)
    response = requests.get(url + "/rest/v1/cities_qol", params={"select": "*"},
                            headers={"apikey": key, "Authorization": "Bearer " + key}, timeout=30)
    response.raise_for_status()
    report = {"audited_at": datetime.now(timezone.utc).isoformat(), "cities": {}}
    for row in response.json():
        code = row["insee_code"]
        entry = {"snapshot": snapshot(row), "audited_at": report["audited_at"]}
        try:
            entry["geocoding"] = geocode(row["city_name"], insee_code=code)
        except Exception as error:
            entry["geocoding_error"] = str(error)
        try:
            risks = parse_risks_data(get_risks_by_commune(code))
            if risks["code_insee"] != code:
                raise ValueError("Commune absente de la réponse GASPAR")
            entry["risks"] = risks
            entry["risks"]["matches_stored"] = risks["total_risks"] == row.get("risks_count")
        except Exception as error:
            entry["risks_error"] = str(error)
        cache = DATA_DIR / f"dvf_{DEFAULT_DVF_YEAR}_{DEPARTMENTS.get(code)}.csv"
        if cache.exists():
            frame = pd.read_csv(cache, dtype={"code_commune": str}, low_memory=False)
            entry["dvf"] = get_commune_stats(frame, code, row["city_name"])
            if entry["dvf"]:
                entry["dvf"].update({"year": DEFAULT_DVF_YEAR, "cache_file": cache.name,
                                     "cache_modified_at": datetime.fromtimestamp(cache.stat().st_mtime, timezone.utc).isoformat(),
                                     "source": f"https://files.data.gouv.fr/geo-dvf/latest/csv/{DEFAULT_DVF_YEAR}/departements/{DEPARTMENTS[code]}.csv.gz"})
        else:
            entry["dvf_error"] = "Cache absent (DVF ne couvre notamment pas le Bas-Rhin)."
        if live:
            try:
                entry["poi_commune"] = get_commune_poi_counts(code)
            except Exception as error:
                entry["poi_commune"] = {"status": "unavailable", "scope": "commune", "insee_code": code, "error": str(error)}
            if OPENAQ_API_KEY:
                try:
                    entry["air"] = get_air_quality_openaq(row["city_name"], row["latitude"], row["longitude"])
                except Exception as error:
                    entry["air_error"] = str(error)
            else:
                entry["air_error"] = "Clé OpenAQ absente : aucune nouvelle mesure vérifiée."
        report["cities"][code] = entry
        print(row["city_name"], "GASPAR:", entry.get("risks", {}).get("total_risks"),
              "DVF échantillon:", (entry.get("dvf") or {}).get("nb_ventes_totales"),
              "OSM:", entry.get("poi_commune", {}).get("status", "non recollecté"), flush=True)
        # Sauvegarde progressive : un arrêt ne perd pas les communes déjà vérifiées.
        PUBLIC_DIR.mkdir(exist_ok=True, parents=True)
        (PUBLIC_DIR / "audit.json").write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8")
    PUBLIC_DIR.mkdir(exist_ok=True, parents=True)
    encoded = json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False)
    (PUBLIC_DIR / "audit.json").write_text(encoded, encoding="utf-8")
    (ROOT / "data/source-audit.json").write_text(encoded, encoding="utf-8")
    print("Audit enregistré ; aucun enregistrement Supabase modifié.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="Recollecter aussi OSM et OpenAQ si la clé est configurée")
    run_audit(live=parser.parse_args().live)
