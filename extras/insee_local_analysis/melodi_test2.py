import requests

# Test de la route avec 'V' majuscule
url = "https://api.insee.fr/melodi/V1/datasets"
headers = {"Accept": "application/json"}

response = requests.get(url, headers=headers)
print(f"Code : {response.status_code}")
print(f"URL finale : {response.url}")
