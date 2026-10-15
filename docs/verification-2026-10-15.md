# Vérification du 15 octobre 2026

## Collecte quotidienne

Le workflow `.github/workflows/update-data.yml` lance `python -m src.main_pipeline`.
La programmation est `17 4 * * *`, soit 04 h 17 UTC : 06 h 17 à Paris en été, 05 h 17 en hiver. L'heure réelle peut être retardée par GitHub.

Le [lancement automatique n° 3](https://github.com/clemence6/france-quality-of-life-3/actions/runs/38710869176) a démarré le 15 octobre à 11 h 09, heure de Paris, et a réussi en 3 min 27 s. Son bilan est de 11/11 villes mises à jour, avec une nouvelle collecte de services et dix collectes précédentes conservées après des erreurs Overpass. Les neuf villes ajoutées ensuite ont été chargées le même jour. Le script de la branche `main` contient maintenant les vingt villes.

## Ce que signifie « à jour »

Les vingt observations Supabase portent une date de mise à jour du 15 octobre et leurs métadonnées correspondent aux valeurs affichées. Cela ne signifie pas que tous les chiffres ont été mesurés le 15 octobre.

| Source | État vérifié |
| --- | --- |
| DVF | Prix disponibles pour 19/20 villes, calculés sur des ventes de 2025. Strasbourg n'est pas couverte. Une nouvelle collecte ne transforme pas ces ventes en prix de 2026. |
| OpenStreetMap / Overpass | 8 collectes du 15 octobre, 10 du 14 octobre conservées avec leur date, 2 indisponibles : Brest et Clermont-Ferrand. |
| OpenAQ | Mesures PM2.5 disponibles pour 18/20 villes, datées du 15 octobre entre 01 h et 11 h, heure de Paris. Pas de mesure disponible pour Dijon et Toulon. Ce ne sont pas des mesures instantanées. |
| Géorisques / GASPAR | Listes consultées pour les 20 communes lors des collectes du jour. Cela ne signifie pas qu'un nouveau risque est apparu ce jour-là. |

Les valeurs indisponibles ne sont pas remplacées par zéro. Les services comptés dans OSM ne constituent pas un inventaire exhaustif des équipements réels.

## Vérifications du site

- 29 tests Python réussis.
- Vérifications JavaScript de la carte, des données, des sept graphiques et de la version anglaise réussies.
- Bascule français / anglais et chargement des vingt villes vérifiés dans le navigateur local, sans erreur de console.
- La publication Firebase ne comprend que le dossier `web`. Les clés privées restent hors du site.

## Publication

Après confirmation de l'acceptation des conditions par la propriétaire, le projet `ou-habiter-clemence` a été créé et le site publié avec succès sur Firebase Hosting le 15 octobre 2026.

- [Site en français](https://ou-habiter-clemence.web.app/).
- [Site en anglais](https://ou-habiter-clemence.web.app/en/).
- Version Hosting publiée : `d279ef1adf4d882d`.

Les deux pages et les fichiers JavaScript, CSS, configuration publique et provenance répondent en HTTPS avec un statut 200 et correspondent aux fichiers locaux. Le chargement des vingt villes, une fiche Montpellier, les dates des sources et le comparateur Montpellier / Angers ont été vérifiés sur l'hébergement public. Le passage français / anglais fonctionne ; aucune erreur JavaScript n'a été constatée pendant ces vérifications.

Les chemins `/.env`, `/.firebaserc` et `/src/main_pipeline.py` répondent 404. Aucune des clés privées Supabase ou OpenAQ du fichier local `.env` n'a été trouvée dans les fichiers publics contrôlés. La connexion aux données utilise la clé publique anon prévue à cet effet.

Le cron continue d'actualiser Supabase indépendamment de Firebase : les observations disponibles sont chargées à chaque visite sans redéploiement quotidien du site.
