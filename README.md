# Où habiter? — Where to live in France

**Public data, clearer choices.** An interactive data analysis project comparing housing prices, local services, air quality and recorded risks across **20 French cities**.

[Explore the live app →](https://ou-habiter-clemence.web.app/en/) · [Version française](https://ou-habiter-clemence.web.app/) · [View the daily audit](https://ou-habiter-clemence.web.app/data/audit.json) · [Connect on LinkedIn](https://www.linkedin.com/in/clemence-core-462648216/)

## The question

**Which cities fit a housing budget and the services that matter most?**

Choose a maximum apartment price per square metre and a service priority, such as parks or pharmacies. The app returns up to three cities within budget, ordered by the number of mapped services in that category. Explore the map, compare two cities and use the dashboard to understand the trade-offs.

## What this project demonstrates

- **Data collection:** Python scripts query APIs and download departmental property transaction files.
- **Data preparation:** pandas standardises municipality codes, combines city arrondissements, converts numeric fields and filters usable residential sales.
- **Analysis:** separate median prices for houses and apartments, municipal service counts and comparisons in their original units.
- **Data quality:** automated tests, traceable observations and a daily audit of the data actually published.
- **Delivery:** PostgreSQL through Supabase, scheduled GitHub Actions workflows and an interactive bilingual website hosted on Firebase.

## Data and analytical choices

| Question | Source | Output |
| --- | --- | --- |
| What does buying a home cost? | [DVF · French tax authority](https://www.data.gouv.fr/datasets/demandes-de-valeurs-foncieres-geolocalisees) | Median €/m², sample sizes and transaction period, separately for apartments and houses |
| Which everyday services are mapped? | [OpenStreetMap · Overpass API](https://wiki.openstreetmap.org/wiki/Overpass_API/Overpass_QL) | Seven service categories counted within municipal boundaries |
| What is measured in the air nearby? | [OpenAQ](https://docs.openaq.org/resources/latest) | A PM2.5 station reading in µg/m³, with its location and measurement time |
| Which hazards are recorded? | [Géorisques · GASPAR](https://www.georisques.gouv.fr/donnees/bases-de-donnees/procedures-administratives-relatives-aux-risques) | Distinct natural and technological hazard types for each municipality |
| Where should each city appear? | [IGN geocoding](https://cartes.gouv.fr/aide/fr/guides-utilisateur/utiliser-les-services-de-la-geoplateforme/geocodage/) | Coordinates checked against the municipality’s INSEE code |

The indicators retain their own units rather than being combined into an arbitrary “best city” score. Property prices describe a filtered sales sample; service counts describe mapped objects. Station readings retain their own timestamps. The app explains these definitions alongside the charts.

## How it works

```text
Public files & APIs
        ↓
Python · pandas · municipality matching & cleaning
        ↓
Supabase · PostgreSQL + public source metadata
        ↓
Data audit · reproducibility, units, dates & consistency
        ↓
Interactive map, comparisons & SVG charts · Firebase
```

### Daily collection and audit

[update-data.yml](.github/workflows/update-data.yml) runs daily at **04:17 UTC**, and supports manual runs. GitHub can delay scheduled execution.

1. Run the Python tests, then collect and update the city data.
2. Check the 20 expected cities against the published provenance and recalculate DVF results from the downloaded CSV files.
3. Publish the [audit report](https://ou-habiter-clemence.web.app/data/audit.json), retain the run artefacts for 30 days and list any issues in the Actions summary.

The audit checks stored values, municipal scope, service counts, dates and PM2.5 units. It distinguishes collection time from the age of the OSM server database. A recent valid service count can be retained for up to seven days during an API outage, with its original date. Missing observations remain missing. An inconsistent audit makes the workflow fail.

The current property dataset covers **2025**. Strasbourg is outside DVF coverage. A daily collection refreshes the available source data; it does not create new property transactions when the source is unchanged.

## Run locally

Python 3.12 is used in GitHub Actions. Node.js is used for frontend checks; the website itself is static.

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

For your own Supabase project, apply [sql/schema.sql](sql/schema.sql), then configure:

- `.env`: `SUPABASE_URL`, private `SUPABASE_KEY` and `OPENAQ_API_KEY` for the pipeline.
- `web/config.js`: the public Supabase URL and **anon** key for the read-only website.

Private keys belong in local environment variables or GitHub Actions secrets. Keep `.env` out of Git. The website must never receive a service-role or OpenAQ key.

```powershell
python -m src.main_pipeline
python -m src.daily_audit --publish
python -m http.server 8000 --directory web
```

Open [localhost:8000](http://localhost:8000). The audit uses DVF files downloaded by the pipeline. For an additional manual source check, see `python -m src.audit_sources --help`.

## Quality checks and deployment

```powershell
python -m unittest discover -s tests -v
python scripts/build_english.py
node tests/frontend-integrity.cjs
node tests/dashboard-integrity.cjs
node tests/english-integrity.cjs
```

French source files and the reviewed translation catalogue generate the English pages. [firebase.json](firebase.json) runs the frontend checks before publishing `web/`. Data and audit updates are delivered through Supabase without redeploying the website.

```powershell
firebase deploy --only hosting --project ou-habiter-clemence
```

## Project structure

| Path | Purpose |
| --- | --- |
| `src/extract/` | API clients and DVF processing |
| `src/main_pipeline.py` | Collection and Supabase updates |
| `src/daily_audit.py` | Daily audit of published values and reproducible calculations |
| `src/provenance.py` | Observation metadata and public report publication |
| `web/` | MapLibre map, SVG dashboard and bilingual interface |
| `translations/` | English text catalogue and hazard labels |
| `tests/` | Data integrity, pipeline and frontend checks |
| `sql/` | Database schema and public-read policy |
| `.github/workflows/` | Scheduled collection and manual publication check |

Further methodological notes are available in French in [docs/AUDIT_SOURCES.md](docs/AUDIT_SOURCES.md). Exploratory INSEE work is kept separately in `extras/insee_local_analysis/`.

---

Built by **Clemence Core** · [LinkedIn](https://www.linkedin.com/in/clemence-core-462648216/) · [GitHub](https://github.com/clemence6)
