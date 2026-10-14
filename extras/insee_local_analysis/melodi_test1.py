import time
import requests

BASE_URL = "https://api.insee.fr/melodi/V1"

def query_melodi(endpoint: str, params: dict = None):
    """Interroge l'API Melodi de l'INSEE."""
    url = f"{BASE_URL.rstrip('/')}/{endpoint.lstrip('/')}"
    headers = {"Accept": "application/json"}
    
    response = requests.get(url, headers=headers, params=params)
    
    # Gestion du quota (30 requêtes / minute)
    if response.status_code == 429:
        retry_after = int(response.headers.get("Retry-After", 2))
        print(f"Limite atteinte. Pause de {retry_after} secondes...")
        time.sleep(retry_after)
        return query_melodi(endpoint, params)
        
    response.raise_for_status()
    return response.json()

if __name__ == "__main__":
    try:
        resultat = query_melodi("datasets")
        print(resultat)
    except requests.exceptions.HTTPError as err:
        print(f"Erreur HTTP : {err}")
