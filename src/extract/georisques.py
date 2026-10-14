"""
Récupération des risques naturels et technologiques via l'API Géorisques (GASPAR).
Documentation : https://www.georisques.gouv.fr/doc-api

Pas de clé API nécessaire. Les endpoints acceptent un code INSEE de commune.
"""

import requests

REQUEST_TIMEOUT = 10
GEORISQUES_BASE_URL = "https://georisques.gouv.fr/api/v1"


def get_risks_by_commune(code_insee: str) -> dict:
    """
    Récupère la synthèse brute des risques (GASPAR) pour une commune via son code INSEE.
    Limite d'appel : 1000 requêtes/minute par IP.
    """
    url = f"{GEORISQUES_BASE_URL}/gaspar/risques"
    params = {"code_insee": code_insee}

    response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.json()


def parse_risks_data(risks_data: dict) -> dict:
    """
    Extrait un résumé structuré des risques à partir de la réponse brute API :
    - Code INSEE et nom de la commune
    - Nombre total de risques distincts
    - Liste complète des libellés de risques
    """
    results = risks_data.get("data", [])
    if not results:
        return {
            "code_insee": None,
            "commune": None,
            "total_risks": None,
            "risks": [],
        }

    commune_info = results[0]
    commune_name = commune_info.get("libelle_commune")
    code_insee = commune_info.get("code_insee")
    risques_detail = commune_info.get("risques_detail")
    if not isinstance(risques_detail, list):
        raise ValueError("Réponse GASPAR sans liste de risques exploitable")

    # Extraction et dédoublonnage des libellés de risques
    risk_names = sorted(
        list(
            {
                r.get("libelle_risque_long")
                for r in risques_detail
                if r.get("libelle_risque_long")
            }
        )
    )

    return {
        "code_insee": code_insee,
        "commune": commune_name,
        "total_risks": len(risk_names),
        "risks": risk_names,
    }


def count_risk_types(risks_data: dict) -> int:
    """Rétrocompatibilité : compte uniquement le nombre de risques."""
    parsed = parse_risks_data(risks_data)
    return parsed["total_risks"]


if __name__ == "__main__":
    # Test avec Toulon (83137)
    raw_data = get_risks_by_commune("83137")
    summary = parse_risks_data(raw_data)

    print(f"Commune : {summary['commune']} ({summary['code_insee']})")
    print(f"Nombre de risques : {summary['total_risks']}")
    print("Détail des risques :")
    for risk in summary["risks"]:
        print(f" - {risk}")
