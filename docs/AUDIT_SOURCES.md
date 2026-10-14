# Audit des sources et décision méthodologique

Audit commencé le 13 octobre 2026 et actualisé le 14 octobre 2026 sur les
11 lignes publiques de `cities_qol`.
Le résultat détaillé est dans `web/data/audit.json`, également conservé dans
`data/source-audit.json`. Aucune ligne Supabase n'a été modifiée pendant cet audit.

## Décision : indicateurs séparés, pas de classement global

L'ancien score ne permettait pas de conclure quelle ville offre la meilleure
qualité de vie. Une normalisation min–max sur 11 villes attribuait 0 et 100 aux
extrêmes de cet échantillon, sans seuil de qualité externe. Elle associait une
valeur neutre de 50 aux observations manquantes. Les erreurs GASPAR/OSM pouvaient
être enregistrées comme zéro, donc récompensées ou pénalisées à tort.

Le choix des pondérations ne corrige pas ces défauts de mesure. Prix d'achat,
activité immobilière, présence de catégories de risques, concentration d'un
polluant et objets OSM locaux ne sont pas des mesures interchangeables du
bien-être. Le score, les gagnants et les curseurs de pondération sont supprimés.

## Ce qui a été effectivement vérifié

| Source | Vérification réalisée | Présentation dans le site |
| --- | --- | --- |
| Supabase | Lecture publique des 11 villes ; instantané des champs associés à chaque audit | Les métadonnées sont ignorées si elles ne correspondent plus à la ligne chargée |
| IGN | Requête officielle par code INSEE et type `municipality` pour chaque ville ; code retourné contrôlé | Position documentée, pas une mesure de la population ou de la centralité |
| GASPAR | API officielle reconsultée pour les 11 communes ; conservation des libellés distincts | Liste datée, sans score d'intensité ou de danger |
| DVF | Recalcul des 10 caches départementaux présents ; périodes, taille d'échantillon et exclusions conservées | Médianes maisons et appartements séparées ; données de cache, sans certification de représentativité |
| OSM | Documentation et requête relues ; ajout des relations, rejet des réponses Overpass partielles ; collecte complémentaire tentée avec `--live` | Nouvelles valeurs utilisées lorsque la collecte réussit ; échecs conservés dans le rapport, anciens zéros non certifiés masqués |
| OpenAQ | Documentation v3 et code relus ; défauts de sélection/polluant/date corrigés ; tentative de lecture si une clé est disponible | Anciennes valeurs masquées faute de métadonnées ; un relevé récent n'est affiché que si polluant, unité et date sont conservés |
| INSEE | État réel de l'intégration contrôlé ; documentation du comparateur consultée | Aucune donnée INSEE présentée comme collectée ; lien vers le portrait officiel |

Ces vérifications ne certifient pas chaque observation historique. Une réponse
d'API récente n'est pas une garantie permanente ; un calcul refait sur un cache
n'est pas une nouvelle extraction de la DGFiP. Ces distinctions sont visibles.

La collecte complémentaire du 14 octobre a réussi pour les compteurs OSM de
10 villes ; Toulouse a échoué sur les trois endpoints (timeouts / erreurs 504).
Des relevés PM2.5 avec unité, station, distance et date ont été trouvés pour
10 villes ; aucun relevé récent exploitable n'a été trouvé pour Toulon. La clé
OpenAQ configurée a permis la lecture ; elle n'est jamais publiée dans le site.

## Immobilier : correction conservatrice

La documentation Geo-DVF précise que `id_mutation` sert à grouper les lignes.
Diviser la valeur totale d'une mutation par la surface de chaque ligne peut
produire des prix erronés ; le nombre de lignes n'est pas le nombre de ventes.

Sans identifiant de local fiable, le nouveau calcul retient seulement les
mutations à une ligne dans tout le département **avant** le filtre de commune,
de nature et de type. Les lignes d'une mutation complexe situées hors commune
ou correspondant à une dépendance ne disparaissent pas avant ce contrôle.

Filtres : nature `Vente`, appartement ou maison, valeur et surface positives,
prix entre 200 et 20 000 €/m². Ces bornes sont des conventions de nettoyage,
pas des seuils officiels. La médiane par type est masquée sous 10 observations.
Les codes des arrondissements de Paris, Lyon et Marseille sont agrégés.

Cette sélection exclut beaucoup de ventes complexes et peut biaiser les
médianes. Elle sert à examiner un échantillon explicite, pas à estimer avec
précision le prix de tous les logements d'une ville. Les périodes affichées
sont les dates réellement présentes dans les caches. La comparaison signale
les périodes différentes. Strasbourg reste sans valeur DVF : le Bas-Rhin
n'est pas couvert par la diffusion DVF de référence.

## Air : correction de la collecte future

La recherche nationale limitée aux 100 premières stations est remplacée par
une recherche locale paginée à 25 km maximum. Le pipeline transmet les
coordonnées de la commune déjà contrôlée. Les stations demandées sont fixes et
de référence. La distance est contrôlée après réception.

Seuls les PM2.5 en µg/m³ alimentent la colonne historique `air_quality_score`.
Il n'y a plus de repli sur PM10, NO2, O3 ou une mesure quelconque. Les mesures
négatives, non finies, non datées, dans le futur ou âgées de plus de 48 heures
au moment de la collecte sont rejetées. Un relevé ponctuel reste un relevé de
station ; il ne devient pas un indice communal ni une exposition annuelle.

## Métadonnées et maintenance

`python -m src.audit_sources` reconsulte IGN/GASPAR, recalcule les caches DVF et
écrit le rapport public en lecture seule. L'option `--live` ajoute la collecte
OSM et tente OpenAQ si la clé est configurée. Les erreurs restent consultables
par ville ; elles ne sont pas transformées en zéro. Le pipeline d'écriture publie les
métadonnées dans `web/data/provenance.json`, liées aux valeurs renvoyées par
Supabase après l'upsert. Aucun changement du schéma Supabase n'est nécessaire.
Il faut déployer les fichiers de `web/data/` avec le reste du site.

Les certificats de confiance Windows ont été utilisés pour l'audit dans cet
environnement ; la validation TLS n'a pas été désactivée. Si `requests` échoue
à valider les certificats dans le venv, corriger son magasin de confiance ;
ne pas utiliser `verify=False`.

Le globe utilise MapLibre GL JS 5.6.2 intégré au projet et les contours Natural
Earth 1:110m dans le domaine public. Ils donnent une vue générale, sans précision
de limites communales. À fort zoom, les rues utilisent les tuiles OpenStreetMap
avec attribution visible et cache navigateur normal. Aucun téléchargement en
masse ni mode hors ligne de ces tuiles n'est proposé.

## Références primaires consultées

- [DGFiP — Demandes de valeurs foncières](https://www.data.gouv.fr/datasets/demandes-de-valeurs-foncieres)
- [Etalab — DVF géolocalisées et définition de `id_mutation`](https://www.data.gouv.fr/datasets/demandes-de-valeurs-foncieres-geolocalisees)
- [Géorisques — base GASPAR](https://www.georisques.gouv.fr/donnees/bases-de-donnees/procedures-administratives-relatives-aux-risques)
- [OpenAQ — recherche de stations, radius et pagination](https://docs.openaq.org/api/operations/locations_get_v3_locations_get)
- [OpenAQ — derniers relevés et horodatages](https://docs.openaq.org/api/operations/location_latest_get_v3_locations__locations_id__latest_get)
- [OpenStreetMap — Overpass QL](https://wiki.openstreetmap.org/wiki/Overpass_API/Overpass_QL)
- [IGN — service de géocodage](https://cartes.gouv.fr/aide/fr/guides-utilisateur/utiliser-les-services-de-la-geoplateforme/geocodage/)
- [INSEE — base du comparateur de territoires](https://www.insee.fr/fr/statistiques/2521169)
- [Natural Earth — domaine public](https://www.naturalearthdata.com/about/terms-of-use/)
- [OpenStreetMap — politique d'utilisation des tuiles](https://operations.osmfoundation.org/policies/tiles/)

## Nouvelle collecte communale — 14 octobre 2026

À la demande de l'utilisateur, les services sont désormais recensés à l'échelle
de la commune entière. `python -m src.refresh_commune_services` enrichit l'audit
existant en lecture seule, sans modifier les autres sources ni Supabase.

La requête Overpass sélectionne la relation administrative de niveau 8 par
`ref:INSEE`, vérifie qu'elle est unique, contrôle la zone dérivée de cette
relation, puis vérifie la présence des sept sorties de comptage. Une zone
absente ou une réponse partielle ne devient jamais une série de zéros.
Les résultats figurent dans `poi_commune`, avec périmètre, relation OSM, date
de collecte et date de la base OSM. Les anciennes métadonnées `poi` à 1 km
restent dans le rapport historique, mais sont exclues des graphiques actuels.

Les objets OSM d'une même catégorie sont comptés sur tout le territoire de la
commune. Plusieurs objets peuvent parfois représenter le même établissement ;
ce n'est donc pas un recensement officiel exhaustif des équipements physiques.
Les catégories ne sont pas additionnées en un score et le total dépend aussi
de la taille de la commune. Les fiches, comparaisons et graphiques utilisent
le même périmètre communal. Le pipeline et l'option d'audit `--live` utilisent
également cette nouvelle collecte pour les prochains chargements.

Documentation : https://wiki.openstreetmap.org/wiki/Overpass_API/Overpass_QL
et https://wiki.openstreetmap.org/wiki/Key:ref:INSEE.

La collecte communale a réussi pour les onze villes, Montpellier comprise après
une nouvelle tentative. Le serveur public Private.coffee (successeur de Kumi)
figure désormais en premier dans les alternatives Overpass utilisées.
