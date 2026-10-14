"""
Qualité de l'air - Atmo France / Geod'Air.

⚠️ Contrairement à la BAN ou Géorisques, l'accès aux données Atmo France varie
selon les AASQA régionales et peut nécessiter une clé API (Geod'Air) ou passer
par les portails régionaux d'open data. Ce module fournit :

1. Une fonction pour interroger l'API OpenAQ v3 (couverture variable en
   France), avec géocodage + sélection de la station la plus proche.
2. Un point d'extension pour brancher l'API Geod'Air officielle une fois
   ta clé obtenue sur https://www.geodair.fr

⚠️ OpenAQ v2 (sans clé) est dépréciée. La v3 exige une clé API gratuite,
à obtenir sur https://explore.openaq.org/register puis à renseigner dans
OPENAQ_API_KEY dans ton .env.

Documentation Geod'Air : https://www.geodair.fr/dgd/api
"""

import math
from datetime import datetime, timezone, timedelta
import os
import requests
from dotenv import load_dotenv

load_dotenv()

OPENAQ_API_KEY = os.getenv("OPENAQ_API_KEY")
ATMO_API_KEY = os.getenv("ATMO_API_KEY")
REQUEST_TIMEOUT = 10

GEOCODE_URL = "https://data.geopf.fr/geocodage/search"  # Géoplateforme/IGN
OPENAQ_LOCATIONS_URL = "https://api.openaq.org/v3/locations"
OPENAQ_LATEST_URL = "https://api.openaq.org/v3/locations/{location_id}/latest"

# Ordre de préférence pour choisir UN indicateur représentatif de la pollution
# (utilisé par get_primary_pollution_value ci-dessous).
PREFERRED_PARAMETERS = ["pm25", "pm2.5", "pm10", "no2", "o3"]


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distance approximative en km entre deux points GPS (Haversine)."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def get_air_quality_openaq(city: str, latitude: float | None = None, longitude: float | None = None) -> dict | None:
    """
    Dernières mesures de qualité de l'air pour une ville via OpenAQ v3.

    Retourne : {
        "city": ..., "station_id": ..., "station_name": ..., "distance_km": ...,
        "measurements": {"pm25": {"value": 12.3, "unit": "µg/m³"}, ...}
    }
    Les mesures sont désormais structurées (value/unit séparés) plutôt qu'une
    chaîne "valeur unité" — plus sûr à parser côté pipeline.
    """
    if not OPENAQ_API_KEY:
        raise RuntimeError(
            "OPENAQ_API_KEY manquante dans .env. Inscris-toi gratuitement sur "
            "https://explore.openaq.org/register pour obtenir une clé."
        )

    headers = {"X-API-Key": OPENAQ_API_KEY}

    # Étape 1 : géocoder la ville (Géoplateforme, remplace l'ancienne API BAN)
    if latitude is None or longitude is None:
        geo_res = requests.get(
            GEOCODE_URL,
            params={"q": city, "type": "municipality", "limit": 1},
            timeout=REQUEST_TIMEOUT,
        )
        geo_res.raise_for_status()
        features = geo_res.json().get("features", [])
        if not features:
            return None
        target_lon, target_lat = features[0]["geometry"]["coordinates"]
    else:
        target_lat, target_lon = latitude, longitude

    # Étape 2 : récupérer les stations en France
    locations = []
    page = 1
    while True:
        response = requests.get(
            OPENAQ_LOCATIONS_URL, headers=headers,
            params={"iso": "FR", "coordinates": f"{target_lat:.4f},{target_lon:.4f}",
                    "radius": 25000, "limit": 100, "page": page,
                    "monitor": "true", "mobile": "false"},
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        batch = response.json().get("results", [])
        locations.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    if not locations:
        print("Aucune station OpenAQ trouvée pour la France.")
        return None

    # Étape 3 : trier les stations par distance
    valid_locations = []
    for loc in locations:
        coords = loc.get("coordinates", {})
        loc_lat, loc_lon = coords.get("latitude"), coords.get("longitude")
        if loc_lat is not None and loc_lon is not None:
            dist = calculate_distance(target_lat, target_lon, loc_lat, loc_lon)
            if dist <= 25:
                valid_locations.append((dist, loc))
    valid_locations.sort(key=lambda x: x[0])

    # Étape 4 : tester les stations les plus proches jusqu'à en trouver une avec des mesures
    for dist, location in valid_locations:
        location_id = location["id"]

        sensors_map = {}
        for s in location.get("sensors", []):
            s_id = s.get("id")
            p = s.get("parameter", {})
            p_name = (p.get("name") or p.get("displayName") or p.get("slug") or "").lower()
            p_unit = p.get("units") or p.get("unit") or ""
            if s_id:
                sensors_map[s_id] = {"name": p_name, "unit": p_unit}

        latest_response = requests.get(
            OPENAQ_LATEST_URL.format(location_id=location_id),
            headers=headers,
            params={"datetime_min": (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()},
            timeout=REQUEST_TIMEOUT,
        )
        if latest_response.status_code != 200:
            continue

        measurements_raw = latest_response.json().get("results", [])
        if not measurements_raw:
            continue

        measurements = {}
        for m in measurements_raw:
            if "value" not in m:
                continue
            sensor_info = sensors_map.get(m.get("sensorsId"), {})
            param_name = sensor_info.get("name")
            unit = sensor_info.get("unit")

            if not param_name:
                param = m.get("parameter")
                if isinstance(param, dict):
                    param_name = (param.get("name") or param.get("displayName") or "").lower()
                    unit = unit or param.get("units")
                else:
                    param_name = f"capteur_{m.get('sensorsId')}"

            try:
                value = float(m["value"])
            except (TypeError, ValueError):
                continue

            measured_at = (m.get("datetime") or {}).get("utc")
            try:
                stamp = datetime.fromisoformat(measured_at.replace("Z", "+00:00"))
            except (AttributeError, ValueError):
                continue
            if stamp.tzinfo is None:
                continue
            age = datetime.now(timezone.utc) - stamp
            if not math.isfinite(value) or value < 0 or not timedelta(0) <= age <= timedelta(hours=48):
                continue
            measurements[param_name] = {"value": value, "unit": unit or "", "measured_at": measured_at, "sensor_id": m.get("sensorsId")}

        if get_primary_pollution_value({"measurements": measurements}) is not None:
            return {
                "city": city,
                "station_id": location_id,
                "station_name": location.get("name"),
                "distance_km": round(dist, 2),
                "measurements": measurements,
            }

    print(f"Aucune mesure récente disponible sur les stations proches de {city}")
    return {"city": city, "measurements": {}}


def get_primary_pollution_value(air_data: dict | None) -> float | None:
    """
    Extrait uniquement une concentration PM2.5 en µg/m³.
    Ce relevé ponctuel ne constitue pas un indice de qualité de vie.
    Utilisée par le pipeline pour remplir "air_quality_score".
    """
    if not air_data or not air_data.get("measurements"):
        return None

    # Un seul polluant et une seule unité : aucun repli vers NO2/O3/PM10.
    measurements = air_data["measurements"]
    for name in ("pm25", "pm2.5"):
        measurement = measurements.get(name)
        if measurement and measurement.get("unit", "").replace("μ", "µ") == "µg/m³":
            value = measurement.get("value")
            if isinstance(value, (int, float)) and math.isfinite(value) and value >= 0:
                return value
    return None


def get_air_quality_geodair(code_insee: str) -> dict:
    """
    Point d'extension pour l'API officielle Geod'Air (nécessite ATMO_API_KEY).
    À compléter selon la documentation exacte de ton AASQA régionale :
    https://www.geodair.fr/dgd/api
    """
    if not ATMO_API_KEY:
        raise RuntimeError(
            "ATMO_API_KEY manquante dans .env — inscris-toi sur geodair.fr "
            "pour obtenir une clé, ou utilise get_air_quality_openaq() en attendant."
        )
    raise NotImplementedError("À implémenter selon la doc Geod'Air de ta région.")


if __name__ == "__main__":
    data = get_air_quality_openaq("Marseille")
    print(data)
    print("Valeur retenue pour le score :", get_primary_pollution_value(data))
