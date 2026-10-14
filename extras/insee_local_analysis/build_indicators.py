import pandas as pd
from pathlib import Path


# ============================================================
# CONFIGURATION
# ============================================================

INPUT_FILE = Path("data/insee/insee_observations.csv")
OUTPUT_FILE = Path("data/insee/insee_indicators.csv")


# ============================================================
# CHARGEMENT
# ============================================================

df = pd.read_csv(INPUT_FILE)

print("=" * 80)
print("CONSTRUCTION DES INDICATEURS INSEE")
print("=" * 80)

print(f"\nObservations initiales : {len(df)}")


# ============================================================
# UTILITAIRES
# ============================================================

def numeric_value(series):
    """
    Convertit une série en numérique.
    """
    return pd.to_numeric(series, errors="coerce")


def get_measure(dataset, measure):
    """
    Retourne les observations correspondant à un dataset
    et à une mesure précise.
    """

    result = df[
        (df["dataset"] == dataset) &
        (df["FILOSOFI_MEASURE"] == measure)
    ].copy()

    return result


def get_rp_measure(measure):
    """
    Retourne une mesure du recensement.
    """

    result = df[
        (df["dataset"] == "DS_RP_LOGEMENT_PRINC") &
        (df["RP_MEASURE"] == measure)
    ].copy()

    return result


# ============================================================
# DATASET FINAL
# ============================================================

result = pd.DataFrame({
    "code_commune": df["code_commune"].drop_duplicates()
})

# Nom commune
names = (
    df[["code_commune", "nom_commune"]]
    .drop_duplicates()
)

result = result.merge(
    names,
    on="code_commune",
    how="left"
)


# ============================================================
# 1. POPULATION
# ============================================================

population = df[
    (df["dataset"] == "DS_POPULATIONS_REFERENCE") &
    (df["POPREF_MEASURE"] == "PTOT")
].copy()

population["population"] = numeric_value(
    population["OBS_VALUE_NIVEAU"]
)

population = population[
    ["code_commune", "TIME_PERIOD", "population"]
].rename(
    columns={
        "TIME_PERIOD": "annee_population"
    }
)

result = result.merge(
    population,
    on="code_commune",
    how="left"
)


# ============================================================
# 2. FILOSOFI - REVENUS / PAUVRETÉ
# ============================================================

filosofi = df[
    df["dataset"] == "DS_FILOSOFI_CC"
].copy()

filosofi["value"] = numeric_value(
    filosofi["OBS_VALUE_NIVEAU"]
)

# Niveau de vie médian
median = filosofi[
    filosofi["FILOSOFI_MEASURE"] == "MED_SL"
][
    ["code_commune", "TIME_PERIOD", "value"]
].rename(
    columns={
        "TIME_PERIOD": "annee_revenus",
        "value": "niveau_vie_median"
    }
)

result = result.merge(
    median,
    on="code_commune",
    how="left"
)


# Taux de pauvreté
poverty = filosofi[
    filosofi["FILOSOFI_MEASURE"] == "PR_MD60"
][
    ["code_commune", "value"]
].rename(
    columns={
        "value": "taux_pauvrete"
    }
)

result = result.merge(
    poverty,
    on="code_commune",
    how="left"
)


# Rapport interdécile
inequality = filosofi[
    filosofi["FILOSOFI_MEASURE"] == "IR_D9_D1_SL"
][
    ["code_commune", "value"]
].rename(
    columns={
        "value": "rapport_interdecile"
    }
)

result = result.merge(
    inequality,
    on="code_commune",
    how="left"
)


# ============================================================
# 3. EMPLOI
# ============================================================

emploi = df[
    df["dataset"] == "DS_RP_EMPLOI_LR_PRINC"
].copy()

emploi["value"] = numeric_value(
    emploi["OBS_VALUE_NIVEAU"]
)

# On conserve uniquement la population totale
emploi_total = emploi[
    emploi["SEX"] == "_T"
].copy()


# Population active
active = emploi_total[
    emploi_total["EMPSTA_ENQ"] == "1"
][
    ["code_commune", "TIME_PERIOD", "value"]
].rename(
    columns={
        "TIME_PERIOD": "annee_emploi",
        "value": "population_active"
    }
)

result = result.merge(
    active,
    on="code_commune",
    how="left"
)


# Emploi
emploi_value = emploi_total[
    emploi_total["EMPSTA_ENQ"] == "1T2"
][
    ["code_commune", "value"]
].rename(
    columns={
        "value": "population_emploi"
    }
)

result = result.merge(
    emploi_value,
    on="code_commune",
    how="left"
)


# Chômage
chomage = emploi_total[
    emploi_total["EMPSTA_ENQ"] == "2"
][
    ["code_commune", "value"]
].rename(
    columns={
        "value": "population_chomage"
    }
)

result = result.merge(
    chomage,
    on="code_commune",
    how="left"
)


# ============================================================
# 4. LOGEMENT
# ============================================================

logement = df[
    df["dataset"] == "DS_RP_LOGEMENT_PRINC"
].copy()

logement["value"] = numeric_value(
    logement["OBS_VALUE_NIVEAU"]
)


# Résidences principales
principal = logement[
    (logement["RP_MEASURE"] == "DWELLINGS") &
    (logement["OCS"] == "DW_MAIN")
][
    ["code_commune", "value"]
].rename(
    columns={
        "value": "residences_principales"
    }
)

result = result.merge(
    principal,
    on="code_commune",
    how="left"
)


# Résidences secondaires
secondary = logement[
    (logement["RP_MEASURE"] == "DWELLINGS") &
    (logement["OCS"] == "DW_SEC_DW_OCC")
][
    ["code_commune", "value"]
].rename(
    columns={
        "value": "residences_secondaires"
    }
)

result = result.merge(
    secondary,
    on="code_commune",
    how="left"
)


# Logements vacants
vacant = logement[
    (logement["RP_MEASURE"] == "DWELLINGS") &
    (logement["OCS"] == "DW_VAC")
][
    ["code_commune", "value"]
].rename(
    columns={
        "value": "logements_vacants"
    }
)

result = result.merge(
    vacant,
    on="code_commune",
    how="left"
)


# ============================================================
# 5. DIPLOMES
# ============================================================

diplomes = df[
    df["dataset"] == "DS_RP_DIPLOMES_PRINC"
].copy()

diplomes["value"] = numeric_value(
    diplomes["OBS_VALUE_NIVEAU"]
)


# Population totale
diplomes_total = diplomes[
    diplomes["SEX"] == "_T"
].copy()


def add_diploma_column(
    education_code,
    column_name
):

    global result

    subset = diplomes_total[
        diplomes_total["EDUC"] == education_code
    ][
        ["code_commune", "value"]
    ].rename(
        columns={
            "value": column_name
        }
    )

    result = result.merge(
        subset,
        on="code_commune",
        how="left"
    )


add_diploma_column(
    "001T100_RP",
    "diplomes_niveau_bas"
)

add_diploma_column(
    "500_RP",
    "diplomes_bac"
)

add_diploma_column(
    "600_RP",
    "diplomes_bac_plus_2"
)

add_diploma_column(
    "700_RP",
    "diplomes_bac_plus_3"
)


# ============================================================
# 6. MOBILITÉ / TRANSPORT
# ============================================================

navettes = df[
    df["dataset"] == "DS_RP_NAVETTES_PRINC"
].copy()

navettes["value"] = numeric_value(
    navettes["OBS_VALUE_NIVEAU"]
)


# Population totale
navettes_total = navettes[
    navettes["SEX"] == "_T"
].copy()


# Voiture
voiture = navettes_total[
    navettes_total["TRANS"] == "1"
][
    ["code_commune", "value"]
].rename(
    columns={
        "value": "navettes_voiture"
    }
)

result = result.merge(
    voiture,
    on="code_commune",
    how="left"
)


# Transports en commun
transport_commun = navettes_total[
    navettes_total["TRANS"] == "5"
][
    ["code_commune", "value"]
].rename(
    columns={
        "value": "navettes_transport_commun"
    }
)

result = result.merge(
    transport_commun,
    on="code_commune",
    how="left"
)


# Vélo
velo = navettes_total[
    navettes_total["TRANS"] == "3"
][
    ["code_commune", "value"]
].rename(
    columns={
        "value": "navettes_velo"
    }
)

result = result.merge(
    velo,
    on="code_commune",
    how="left"
)


# Marche
marche = navettes_total[
    navettes_total["TRANS"] == "2"
][
    ["code_commune", "value"]
].rename(
    columns={
        "value": "navettes_marche"
    }
)

result = result.merge(
    marche,
    on="code_commune",
    how="left"
)


# ============================================================
# NETTOYAGE
# ============================================================

numeric_columns = [
    column
    for column in result.columns
    if column not in [
        "code_commune",
        "nom_commune"
    ]
]

for column in numeric_columns:
    result[column] = pd.to_numeric(
        result[column],
        errors="coerce"
    )


# ============================================================
# EXPORT
# ============================================================

OUTPUT_FILE.parent.mkdir(
    parents=True,
    exist_ok=True
)

result.to_csv(
    OUTPUT_FILE,
    index=False,
    encoding="utf-8-sig"
)


# ============================================================
# RAPPORT
# ============================================================

print("\n")
print("=" * 80)
print("✅ INDICATEURS INSEE CRÉÉS")
print("=" * 80)

print(f"\nLignes : {len(result)}")
print(f"Colonnes : {len(result.columns)}")

print("\nColonnes :")

for column in result.columns:
    print(f"  - {column}")

print("\nValeurs manquantes :")

missing = result.isna().sum()

for column, count in missing.items():

    if count > 0:
        print(f"  - {column} : {count}")

print(f"\nFichier : {OUTPUT_FILE}")
