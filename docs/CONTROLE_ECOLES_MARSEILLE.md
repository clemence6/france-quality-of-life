# Contrôle du comptage scolaire de Marseille — 18 octobre 2026

Le site affiche 747 objets scolaires OpenStreetMap pour Marseille (ligne Supabase actualisée le 18 octobre 2026 à 08 h 52 UTC). Le code compte les nœuds, chemins et relations portant le tag `amenity=school` dans la limite communale OSM identifiée par le code INSEE 13055. Il ne dédoublonne pas les établissements à l'aide d'un identifiant scolaire officiel.

## Pourquoi le libellé « écoles » était trop vague

La [définition OSM](https://wiki.openstreetmap.org/wiki/Tag:amenity%3Dschool) couvre les établissements d'enseignement primaire et secondaire, donc également les collèges et lycées. Elle prévoit plusieurs formes de représentation cartographique. Un total d'objets n'est pas une certification du nombre d'établissements uniques.

Le libellé visible devient « Établissements scolaires ». Une explication indique les niveaux couverts, la possibilité de représentations multiples et la différence avec un annuaire officiel.

## Comparaison avec l'annuaire officiel

L'[Annuaire de l'éducation](https://data.education.gouv.fr/explore/dataset/fr-en-annuaire-education), interrogé le 18 octobre 2026 via son API publique v2.1, donne les résultats suivants pour `code_commune IN ('13055', '13201', …, '13216')` :

| Type | Public | Privé | Total |
| --- | ---: | ---: | ---: |
| École | 444 | 70 | 514 |
| Collège | 68 | 48 | 116 |
| Lycée | 40 | 54 | 94 |
| Total de ces trois catégories | 552 | 172 | 724 |

La requête groupe les résultats par `type_etablissement` et `statut_public_prive`. Les autres catégories de l'annuaire (médico-social, services administratifs, orientation et type non renseigné) ne sont pas ajoutées à ce total.

Les 724 entrées officielles et les 747 objets OSM sont du même ordre de grandeur, mais leurs définitions et leurs dates diffèrent. Cette comparaison n'établit pas que les 747 objets sont tous des établissements uniques et ne mesure pas le nombre exact de doublons. Les maternelles, par exemple, ont un tag OSM distinct dans la définition recommandée.

## Limite de la vérification

Les demandes de détail des objets scolaires aux deux serveurs Overpass configurés ont échoué (HTTP 500 et HTTP 504). Le rapprochement objet par objet, notamment à partir des identifiants UAI, n'a donc pas pu être réalisé. Aucun doublon particulier n'est affirmé comme constaté et le compteur n'a pas été remplacé arbitrairement par un total issu d'un autre périmètre.

Les réponses agrégées de l'annuaire et les informations de collecte du contrôle sont conservées localement dans `.tools/schools-audit/`, hors des fichiers publiés du site.
