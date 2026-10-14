"""Recollecter les services par commune, sans modifier les autres audits ni Supabase.

python -m src.refresh_commune_services
"""
import json
import argparse
import os
import re
import ssl
import tempfile
from pathlib import Path
from datetime import datetime, timezone
import requests
from .extract.overpass_osm import get_commune_poi_counts
from .provenance import snapshot

ROOT = Path(__file__).resolve().parents[1]


def write_json(path, document):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(document, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    temporary.replace(path)


def refresh(retry_unavailable=False):
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
    path = ROOT / "web/data/audit.json"
    report = json.loads(path.read_text(encoding="utf-8"))
    for city in response.json():
        code = city["insee_code"]
        entry = report["cities"].get(code)
        if not entry or entry.get("snapshot") != snapshot(city):
            print(city["city_name"], "instantané modifié : relancer l'audit complet", flush=True)
            continue
        if retry_unavailable and entry.get("poi_commune", {}).get("status") == "available":
            continue
        try:
            entry["poi_commune"] = get_commune_poi_counts(code)
            print(city["city_name"], entry["poi_commune"]["counts"], flush=True)
        except Exception as error:
            entry["poi_commune"] = {"status": "unavailable", "scope": "commune",
                                    "insee_code": code, "error": str(error),
                                    "collected_at": datetime.now(timezone.utc).isoformat()}
            print(city["city_name"], "collecte communale indisponible", flush=True)
        write_json(path, report)
    report["commune_services_refreshed_at"] = datetime.now(timezone.utc).isoformat()
    write_json(path, report)
    write_json(ROOT / "data/source-audit.json", report)
    print("Comptages communaux enregistrés ; aucune écriture Supabase.", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--retry-unavailable", action="store_true", help="Retenter uniquement les communes sans collecte réussie")
    refresh(retry_unavailable=parser.parse_args().retry_unavailable)
