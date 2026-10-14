"""
Récupération de points d'intérêt (POI) autour d'un point via l'API Overpass (OpenStreetMap).
Documentation : https://wiki.openstreetmap.org/wiki/Overpass_API
"""

import time
import re
from datetime import datetime, timezone
import requests

REQUEST_TIMEOUT = 30

# Endpoints Overpass officiels
OVERPASS_ENDPOINTS = [
    "https://overpass.private.coffee/api/interpreter",
    "https://overpass-api.de/api/interpreter",
]

# User-Agent épuré : évite le blocage 406 déclenché par ModSecurity sur les faux User-Agents Mozilla
HEADERS = {
    "User-Agent": "FranceQualityOfLifeScript/1.0 (educational-project)",
}

POI_TAGS = {
    "sport": ("leisure", "fitness_centre"),
    "park": ("leisure", "park"),
    "supermarket": ("shop", "supermarket"),
    "pharmacy": ("amenity", "pharmacy"),
    "school": ("amenity", "school"),
    "restaurant": ("amenity", "restaurant"),
    "hospital": ("amenity", "hospital"),
}


def commune_query(insee_code: str) -> str:
    """Résoudre la commune par son code INSEE, jamais par un nom ambigu."""
    if not re.fullmatch(r"(?:\d{5}|2[AB]\d{3})", insee_code):
        raise ValueError("Code INSEE invalide")
    selectors = "\n".join(
        f'nwr["{key}"="{value}"](area.commune); out count;'
        for key, value in POI_TAGS.values()
    )
    return f'''[out:json][timeout:40];
relation["boundary"="administrative"]["admin_level"="8"]["ref:INSEE"="{insee_code}"]->.boundary;
.boundary out tags;
.boundary map_to_area->.commune;
.commune out tags;
{selectors}
'''


def parse_commune_counts(data: dict, insee_code: str) -> dict:
    """Vérifier le périmètre et les sept sorties avant d'accepter un zéro."""
    if data.get("remark"):
        raise ValueError("Réponse Overpass partielle")
    elements = data.get("elements", [])
    relations = [e for e in elements if e.get("type") == "relation"
                 and e.get("tags", {}).get("ref:INSEE") == insee_code
                 and e.get("tags", {}).get("admin_level") == "8"]
    areas = [e for e in elements if e.get("type") == "area"]
    totals = [e for e in elements if e.get("type") == "count"]
    if len(relations) != 1 or len(areas) != 1:
        raise ValueError("Limite communale absente ou ambiguë dans OpenStreetMap")
    relation = relations[0]
    if areas[0].get("id") != relation["id"] + 3600000000:
        raise ValueError("La zone ne correspond pas à la commune demandée")
    if len(totals) != len(POI_TAGS):
        raise ValueError("Comptage communal incomplet")
    counts = {}
    for category, total in zip(POI_TAGS, totals):
        value = total.get("tags", {}).get("total")
        if value is None or not str(value).isdigit():
            raise ValueError("Compteur Overpass invalide")
        counts[category] = int(value)
    return {"status": "available", "scope": "commune", "insee_code": insee_code,
            "scope_label": relation.get("tags", {}).get("name"), "counts": counts,
            "relation_id": relation["id"], "area_id": areas[0]["id"],
            "method": "osm-commune-nwr-count-v1",
            "source": f'https://www.openstreetmap.org/relation/{relation["id"]}',
            "collected_at": datetime.now(timezone.utc).isoformat(),
            "source_timestamp": data.get("osm3s", {}).get("timestamp_osm_base")}


def get_commune_poi_counts(insee_code: str) -> dict:
    """Compter les services référencés à l'intérieur des limites de la commune."""
    query = commune_query(insee_code)
    errors = []
    for endpoint in OVERPASS_ENDPOINTS:
        try:
            response = requests.post(endpoint, data={"data": query}, headers=HEADERS, timeout=55)
            response.raise_for_status()
            return parse_commune_counts(response.json(), insee_code)
        except (requests.RequestException, ValueError, KeyError) as error:
            errors.append(f"{endpoint}: {error}")
    raise RuntimeError("Collecte communale indisponible : " + " | ".join(errors))


def get_all_poi_counts(latitude: float, longitude: float, radius_m: int = 1000) -> dict:
    """
    Récupère le nombre de POI pour chaque catégorie dans un rayon donné autour des coordonnées GPS.
    """
    query = f"""[out:json][timeout:25];
(
  nwr["leisure"="fitness_centre"](around:{radius_m},{latitude},{longitude});
  nwr["leisure"="park"](around:{radius_m},{latitude},{longitude});
  nwr["shop"="supermarket"](around:{radius_m},{latitude},{longitude});
  nwr["amenity"="pharmacy"](around:{radius_m},{latitude},{longitude});
  nwr["amenity"="school"](around:{radius_m},{latitude},{longitude});
  nwr["amenity"="restaurant"](around:{radius_m},{latitude},{longitude});
  nwr["amenity"="hospital"](around:{radius_m},{latitude},{longitude});
);
out tags;"""

    data = None
    errors = []

    for endpoint in OVERPASS_ENDPOINTS:
        try:
            response = requests.post(
                endpoint,
                data={"data": query},
                headers=HEADERS,
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            res_json = response.json()

            if "elements" in res_json and not res_json.get("remark"):
                data = res_json
                break
        except Exception as e:
            errors.append(f"{endpoint} -> {e}")
            time.sleep(1)

    if data is None:
        details = "\n".join(errors)
        raise RuntimeError(f"Échec de l'extraction Overpass sur tous les serveurs :\n{details}")

    counts = {poi_type: 0 for poi_type in POI_TAGS}

    # Agrégation des POI
    for elem in data.get("elements", []):
        tags = elem.get("tags", {})
        for poi_type, (key, value) in POI_TAGS.items():
            if tags.get(key) == value:
                counts[poi_type] += 1

    return counts


if __name__ == "__main__":
    print("Interrogation d'Overpass API en cours...")
    counts = get_all_poi_counts(45.764043, 4.835659, radius_m=1000)
    print("POI trouvés :", counts)
