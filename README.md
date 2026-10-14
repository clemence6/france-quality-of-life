# Où habiter ? — comprendre où mieux vivre

Un projet de data analyse pour identifier les villes françaises où les conditions de vie pourraient mieux correspondre à vos priorités. Le site associe une carte centrée sur la France, des fiches de villes et un dashboard interactif placé sous la carte.

Les indicateurs restent séparés et documentés : immobilier, services dans la commune, air et risques. Aucun classement global ne transforme ces mesures différentes en une fausse note de qualité de vie.

## Architecture

- `src/main_pipeline.py` : collecte les sources et écrit dans Supabase.
- `src/extract/` : IGN, DVF, Overpass/OpenStreetMap, OpenAQ et GASPAR.
- `src/audit_sources.py` : audit reproductible en lecture seule.
- `src/provenance.py` : métadonnées publiques liées aux lignes Supabase.
- `web/index.html`, `style.css`, `app.js` : carte et interface.
- `web/dashboard.js` : graphiques SVG et filtres, sans dépendance supplémentaire.
- `web/data/` : audit et provenance publics, à déployer avec le site.
- `web/vendor/` : MapLibre GL JS et contours Natural Earth intégrés.
- `sql/schema.sql` : schéma et policy de lecture publique.
- `extras/insee_local_analysis/` : travail INSEE exploratoire, non branché.
- `data/raw/` : caches DVF départementaux.

## Installation du pipeline

Créer un environnement Python et installer les dépendances de requirements.txt. Sur Windows, depuis la racine du projet :

~~~powershell
python -m venv venv
./venv/Scripts/Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
~~~

Renseigner dans .env : SUPABASE_URL et SUPABASE_KEY (clé service_role pour écrire), ainsi que OPENAQ_API_KEY pour la collecte de l'air. Ne jamais exposer une clé service_role ou OpenAQ dans le site. Les scripts INSEE et Geod'Air restent des pistes optionnelles non intégrées.

Pour un nouveau projet Supabase, exécuter sql/schema.sql dans son SQL Editor. La table doit autoriser la lecture publique, tandis que l'écriture reste réservée au pipeline.

## Lancer le site

web/config.js contient l'URL Supabase et sa clé publique anon. Aucun build n'est nécessaire.

~~~powershell
cd web
python -m http.server 8000
~~~

Ouvrir http://localhost:8000. Garder le terminal ouvert ; Ctrl+C arrête le serveur. Après une modification du site, utiliser Ctrl+F5. Les fichiers de web/ peuvent être déployés ensemble sur un hébergement statique.

## Audit et collecte

Depuis la racine, avec le venv activé :

~~~powershell
python -m src.audit_sources
python -m src.audit_sources --live
python -m src.refresh_commune_services
python -m src.main_pipeline
~~~

L'audit ne modifie pas Supabase. Il contrôle IGN/GASPAR et recalcule les caches DVF présents. --live ajoute les comptages OSM par commune et tente OpenAQ si sa clé est configurée. Il écrit web/data/audit.json et data/source-audit.json. Les erreurs sont conservées ; elles ne sont pas transformées en zéro.

Le pipeline principal écrit dans Supabase et sauvegarde web/data/provenance.json. Les métadonnées ne sont utilisées que lorsqu'elles correspondent aux observations chargées. Aucun changement du schéma Supabase n'est nécessaire pour ces fichiers de provenance.

Sur Windows, l'audit utilise les certificats du magasin de confiance système si aucun REQUESTS_CA_BUNDLE explicite n'est défini. La validation TLS reste active.

## Dashboard et méthode

Le [guide du dashboard](docs/DASHBOARD.md) décrit les filtres et les sept modules : prix, écarts entre types de logements, services dans la commune, compromis prix/proximité, air, risques et couverture des données.

Le [rapport méthodologique](docs/AUDIT_SOURCES.md) détaille les sources, les corrections et leurs limites. DVF décrit un échantillon conservateur, OSM les services recensés dans les limites de la commune, OpenAQ un relevé ponctuel de station et GASPAR des types de risques recensés. INSEE n'est pas présenté comme une source de chiffres déjà collectés.

## Vérifications

~~~powershell
python -m unittest discover -s tests -v
node tests/frontend-integrity.cjs
node tests/dashboard-integrity.cjs
~~~

Les contrôles couvrent les manquants, les unités, les mutations DVF complexes, l'association entre observations et métadonnées, les filtres et les sélections vides.

## Mise à jour quotidienne sur GitHub

[Le workflow](.github/workflows/update-data.yml) lance le pipeline chaque jour à
04:17 UTC : 05:17 en hiver et 06:17 en été à Paris. Il peut aussi être lancé
depuis **Actions → Actualiser les données chaque jour → Run workflow**.

Sur le dépôt GitHub, ajouter dans **Settings → Secrets and variables → Actions** :

- `SUPABASE_URL` : URL du projet Supabase.
- `SUPABASE_KEY` : clé privée autorisée à écrire dans la table (service_role).
- `OPENAQ_API_KEY` : clé privée OpenAQ v3.

Les valeurs sont celles du `.env` local. Ne pas publier ce fichier ni placer les
clés privées dans `web/config.js`. Les secrets sont fournis uniquement à la
vérification de configuration et à la collecte.

Le runner vérifie les tests Python puis interroge les sources séquentiellement.
Les fichiers DVF du millésime configuré (2025 actuellement) sont retéléchargés
à chaque exécution ; cela n'invente pas de nouvelles transactions lorsque la
source n'a pas changé. Strasbourg reste sans prix DVF car le Bas-Rhin n'est
pas couvert. L'absence de mesure récente d'air est également possible.

Le pipeline actualise Supabase et publie les métadonnées dans son bucket public
`qol-public-metadata`, créé à la première exécution. Il contient uniquement le
fichier JSON des observations, de leurs sources, dates et calculs ; aucune clé.
Le site récupère automatiquement ce fichier à chaque rechargement, y compris
lorsqu'il tourne sur localhost. Il vérifie que ces informations correspondent
aux chiffres chargés avant de les afficher. Les fichiers locaux restent un repli
si la publication distante n'est pas disponible et s'ils correspondent aux données.

Le workflow enregistre aussi `web/data/provenance.json` dans le dépôt pour garder
une trace des mises à jour. Un push effectué avec `GITHUB_TOKEN` ne déclenche
généralement pas un autre workflow de déploiement ; un éventuel déploiement du
code du site doit être appelé explicitement. La mise à jour des données via
Supabase n'a pas besoin de redéployer le site.

Le bilan et les métadonnées sont conservés 30 jours dans les artefacts Actions.
En cas de panne Overpass, un comptage communal déjà contrôlé peut être conservé
pendant sept jours au maximum. Sa date d'origine reste visible, et la panne est
signalée dans le bilan et la fiche. Les anciennes collectes à 1 km, les données
incomplètes ou trop anciennes ne peuvent pas servir de repli.
Une collecte partielle publie les données disponibles. Elle signale un échec
si une ville, la publication ou une source sans repli valide manque ; les valeurs
indisponibles restent inconnues, jamais remplacées par zéro.
Les erreurs par ville et par source apparaissent dans le résumé du lancement.

Le cron ne fonctionne que sur la branche par défaut. GitHub peut retarder son
exécution et désactive les tâches planifiées d'un dépôt public inactif pendant
60 jours. Voir la [documentation GitHub sur les tâches planifiées](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule).
