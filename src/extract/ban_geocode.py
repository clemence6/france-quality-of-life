"""
Géocodage d'adresses / communes via l'API de géocodage de la Géoplateforme (IGN).
Documentation : https://cartes.gouv.fr/aide/fr/guides-utilisateur/utiliser-les-services-de-la-geoplateforme/geocodage/
Swagger : https://data.geopf.fr/geocodage/openapi

⚠️ L'ancienne API BAN (api-adresse.data.gouv.fr) a été décommissionnée fin
janvier 2026. Ce module utilise le nouveau service, opéré par l'IGN, qui est
"iso-fonctionnel" avec l'ancien (mêmes paramètres de recherche, même format
GeoJSON en retour).

Pas de clé API nécessaire pour les appels unitaires (search/reverse).
Limite : 50 requêtes/seconde par IP.
"""

import requests
REQUEST_TIMEOUT=30

BAN_SEARCH_URL = "https://data.geopf.fr/geocodage/search"
BAN_REVERSE_URL = "https://data.geopf.fr/geocodage/reverse"


def geocode(query: str, city_hint: str | None = None, insee_code: str | None = None) -> dict | None:
    """
    Géocode une adresse ou un nom de commune en coordonnées.

    Exemple :
        geocode("10 rue de la République", city_hint="Lyon")
        geocode("Lyon")

    Retourne un dict {label, latitude, longitude, city, postcode, score}
    ou None si rien trouvé.
    """
    params = {"q": query, "limit": 1}
    if insee_code:
        params.update({"type": "municipality", "citycode": insee_code})
    if city_hint:
        params["q"] = f"{query} {city_hint}"

    response = requests.get(BAN_SEARCH_URL, params=params, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    data = response.json()

    features = data.get("features", [])
    if not features:
        return None

    best = features[0]
    coords = best["geometry"]["coordinates"]  # [lon, lat]
    props = best["properties"]
    if insee_code and props.get("citycode") != insee_code:
        raise ValueError("Le géocodage ne correspond pas à la commune demandée")

    return {
        "label": props.get("label"),
        "latitude": coords[1],
        "longitude": coords[0],
        "city": props.get("city"),
        "postcode": props.get("postcode"),
        "score": props.get("score"),
        "insee_code": props.get("citycode"),
    }


def reverse_geocode(latitude: float, longitude: float) -> dict | None:
    """Retrouve l'adresse/commune la plus proche d'un point lat/lon."""
    params = {"lat": latitude, "lon": longitude}
    response = requests.get(BAN_REVERSE_URL, params=params, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    data = response.json()

    features = data.get("features", [])
    if not features:
        return None

    props = features[0]["properties"]
    return {
        "label": props.get("label"),
        "city": props.get("city"),
        "postcode": props.get("postcode"),
    }


if __name__ == "__main__":
    # Test rapide en ligne de commande : python -m src.extract.ban_geocode
    result = geocode("Lyon")
    print(result)
