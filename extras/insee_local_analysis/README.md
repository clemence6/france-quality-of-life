# INSEE — travail en cours, non branché au pipeline principal

Ces scripts ne sont **pas** appelés par `src/main_pipeline.py` actuellement.
Ils correspondent à une piste explorée pour enrichir le projet avec
population/revenus/emploi, mise de côté pour l'instant car l'API Melodi en
accès direct s'est révélée peu fiable à l'usage (endpoints qui ont changé de
casse/version entre les tests `melodi_test1.py` et `melodi_test2.py`).

- `melodi_test1.py` / `melodi_test2.py` : tentatives d'appel direct à l'API
  Melodi (`api.insee.fr/melodi`). À reprendre en vérifiant la documentation
  à jour sur portail-api.insee.fr avant de les relancer.
- `build_indicators.py` : construit un tableau d'indicateurs (population,
  niveau de vie médian, chômage, logement, diplômes, mobilité) à partir d'un
  **export CSV déjà téléchargé** (`data/insee/insee_observations.csv`), pas
  d'un appel API en direct. Nécessite donc d'exporter manuellement ces
  données depuis le site de l'Insee (ou de finaliser l'appel API Melodi)
  avant de pouvoir tourner.

**Prochaine étape suggérée** : une fois `build_indicators.py` fonctionnel,
ajouter les colonnes `population` et `niveau_vie_median` à la table
`cities_qol` (voir `sql/schema.sql`) et les faire remonter dans
`main_pipeline.py`, puis les afficher dans le dashboard.
