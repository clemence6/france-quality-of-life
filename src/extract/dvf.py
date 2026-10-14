"""
Extraction et analyse des transactions immobilières DVF (Demandes de Valeurs
Foncières), publiées par département sur files.data.gouv.fr/geo-dvf/.

download_dvf_department() télécharge (ou lit depuis le cache local) le CSV
d'un département et retourne un DataFrame.

get_commune_stats() filtre ce DataFrame pour une commune donnée (par code
INSEE en priorité, avec repli sur le nom de commune si besoin) et calcule
des statistiques de prix au m².
"""

from pathlib import Path
import pandas as pd
import requests

BASE_URL = "https://files.data.gouv.fr/geo-dvf/latest/csv"

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Dernier millésime disponible dans l'arborescence Geo-DVF (à ajuster si
# data.gouv.fr publie une année plus récente).
DEFAULT_DVF_YEAR = 2025

ALLOWED_NATURES = ["Vente", "Vente en l'état futur d'achèvement", "Adjudication"]
ALLOWED_TYPES = ["Appartement", "Maison"]


def download_dvf_department(department_code: str, year: int = DEFAULT_DVF_YEAR) -> pd.DataFrame | None:
    """
    Télécharge (ou charge depuis le cache local) le fichier DVF d'un
    département pour une année donnée, et retourne un DataFrame.

    Exemple : download_dvf_department("69", 2025) pour le Rhône.
    """
    department_code = str(department_code).zfill(2)
    cache_path = DATA_DIR / f"dvf_{year}_{department_code}.csv"

    if cache_path.exists():
        return pd.read_csv(cache_path, low_memory=False)

    url = f"{BASE_URL}/{year}/departements/{department_code}.csv.gz"
    print(f"⬇️  Téléchargement DVF {department_code} ({year})...")

    try:
        response = requests.get(url, timeout=120)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"❌ Erreur téléchargement DVF ({department_code}, {year}) : {e}")
        return None

    try:
        import io
        df = pd.read_csv(io.BytesIO(response.content), compression="gzip", low_memory=False)
    except Exception as e:
        print(f"❌ Erreur lecture CSV DVF : {e}")
        return None

    df.to_csv(cache_path, index=False)
    print(f"✅ {len(df):,} lignes DVF chargées pour le département {department_code}")
    return df


def get_commune_stats(df: pd.DataFrame, insee_code: str, city_name: str) -> dict | None:
    """Échantillon conservateur de ventes résidentielles à une seule ligne.

    La valeur foncière est celle de la mutation, pas de chaque ligne. Sans
    identifiant fiable du local, les mutations à plusieurs lignes sont exclues
    avant tout filtre géographique/type. On ne prétend pas couvrir le marché.
    """
    required = {"id_mutation", "date_mutation", "nature_mutation", "valeur_fonciere",
                "code_commune", "type_local", "surface_reelle_bati"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Colonnes DVF manquantes : {sorted(missing)}")
    data = df.copy()
    codes = data["code_commune"].astype(str).str.replace(r"\.0$", "", regex=True).str.zfill(5)
    target = str(insee_code).zfill(5)
    arrondissements = {
        "75056": [f"75{i:03d}" for i in range(101, 121)],
        "69123": [f"69{i:03d}" for i in range(381, 390)],
        "13055": [f"13{i:03d}" for i in range(201, 217)],
    }
    mask = codes.isin([target, *arrondissements.get(target, [])])
    city_rows = data.loc[mask]
    if city_rows.empty:
        return None
    # Comptage sur TOUT le département : exclut aussi un bien d'une mutation
    # qui comporte d'autres lignes hors de la commune ou hors du résidentiel.
    sizes = data.groupby("id_mutation")["id_mutation"].transform("size")
    sample = data.loc[mask & sizes.eq(1) & data["id_mutation"].notna()
                      & data["nature_mutation"].eq("Vente")
                      & data["type_local"].isin(ALLOWED_TYPES)].copy()
    sample["value"] = pd.to_numeric(sample["valeur_fonciere"], errors="coerce")
    sample["surface"] = pd.to_numeric(sample["surface_reelle_bati"], errors="coerce")
    sample = sample.loc[(sample["value"] > 0) & (sample["surface"] > 0)].copy()
    sample["prix_m2"] = sample["value"] / sample["surface"]
    before_threshold = len(sample)
    sample = sample.loc[sample["prix_m2"].between(200, 20000)]
    periods = pd.to_datetime(city_rows["date_mutation"], errors="coerce").dropna()
    def median(frame):
        return round(float(frame["prix_m2"].median()), 2) if len(frame) >= 10 else None
    by_type = {}
    for kind, label in [("Appartement", "apartment"), ("Maison", "house")]:
        group = sample.loc[sample["type_local"].eq(kind)]
        by_type[label] = {"median_price_m2": median(group), "sample_count": len(group)}
    return {
        "commune": city_name,
        "nb_ventes_totales": len(sample),
        "prix_m2_median_global": median(sample),
        "by_type": by_type,
        "period_start": periods.min().date().isoformat() if len(periods) else None,
        "period_end": periods.max().date().isoformat() if len(periods) else None,
        "source_rows": len(city_rows),
        "source_mutations": int(city_rows["id_mutation"].nunique()),
        "excluded_by_price": before_threshold - len(sample),
        "method": "single-row-sale-v2",
        "limitations": "Ventes à une seule ligne ; mutations complexes exclues. Seuil de 200 à 20 000 €/m². Médiane masquée si moins de 10 observations. Échantillon non représentatif du marché total.",
    }
