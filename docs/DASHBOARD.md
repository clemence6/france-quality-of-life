# Où habiter ? — dashboard des conditions de vie

Le dashboard se trouve sous la carte centrée sur la France. Il aide à repérer
les villes où les conditions de vie pourraient mieux correspondre aux priorités
du visiteur, sans fabriquer un classement global à partir d'unités différentes.

## Interactions

- Les boutons de villes définissent le périmètre commun à tous les graphiques.
- « Toutes les villes » réinitialise ce périmètre.
- Le sélecteur immobilier distingue maisons et appartements.
- Le module budget filtre les villes selon un prix maximum pour les appartements, puis propose jusqu’à trois villes classées selon le service prioritaire choisi.
- Un clic sur une barre ou un point sélectionne la ville et la met en évidence
  dans les graphiques de prix et de compromis. Sa fiche est ouverte sur la carte.
- Les infobulles et les tableaux accessibles donnent les valeurs, les effectifs,
  les stations ou les périodes selon le graphique.
- La matrice de risques propose un filtre thématique descriptif. Il s'agit
  d'un regroupement de présentation, pas d'une classification officielle.

## Choix analytiques

### Budget maximum et priorité de service

Le module « Votre budget, vos priorités : quelles villes explorer ? » utilise le budget maximum saisi pour les appartements et une catégorie de services au choix. Le budget initial est de 3 000 €/m² ; les filtres de villes du dashboard restent applicables.

Les villes doivent avoir un prix d'appartement et un comptage communal documentés pour le service choisi. Le prix médian doit être inférieur ou égal au budget. Les villes admissibles sont triées par nombre de services décroissant, puis par prix croissant en cas d'égalité, puis par nom. Seules les trois premières sont proposées. Un ou deux résultats sont possibles ; aucun résultat hors budget n'est ajouté. Les années de prix doivent être identiques parmi les villes admissibles.

Un zéro documenté est accepté, une valeur manquante est exclue. Les dates de collecte et le nombre de ventes analysées restent visibles. Les comptages bruts favorisent potentiellement les grandes communes et ne mesurent ni l'accessibilité depuis un quartier, ni la qualité des équipements. Ce classement concerne uniquement le service choisi parmi les villes dans le budget, sans score global de qualité de vie.

Le libellé scolaire est « Établissements scolaires » car le tag OSM couvre l'enseignement primaire et secondaire. Le total d'objets OSM ne certifie pas un nombre d'établissements uniques. Voir le contrôle de Marseille du 18 octobre 2026 dans `CONTROLE_ECOLES_MARSEILLE.md`.

| Vue | Question | Précaution |
| --- | --- | --- |
| Barres de prix | Quel budget au m² dans l'échantillon ? | Axe commençant à zéro ; même type de logement ; effectifs et dates conservés |
| Points reliés | Comment diffèrent les médianes maisons/appartements ? | Deux marchés distincts ; l'écart ne prédit pas le prix d'un même bien |
| Matrice de services | Quels objets sont cartographiés dans les limites de la commune ? | Valeurs brutes ; couleur propre à chaque colonne de la sélection ; manquants hachurés |
| Budget et priorité | Quelles villes ont le plus de services choisis dans ce budget ? | Prix médian des appartements ; comptages OSM bruts ; données manquantes exclues ; au plus trois propositions |
| Relevés PM2.5 | Que disent les dernières observations de stations ? | Ordre alphabétique ; unité identique ; horaires et distances visibles ; pas de classement sanitaire |
| Matrice GASPAR | Quels libellés sont recensés par commune ? | Catégories non additionnées ; présence différente de probabilité ou de gravité |
| Couverture | Quelles données peut-on effectivement examiner ? | Chaque source a son dénominateur et ses limites ; absence différente de zéro |

Les quatre KPI décrivent le périmètre sélectionné, les villes ayant au moins
une médiane immobilière documentée, le cumul des ventes de l'échantillon DVF et
la couverture des collectes OSM. Le cumul des ventes ne représente pas le marché
total. La médiane commentée dans le bandeau est une **médiane entre villes**,
avec une ville = une observation, pas la médiane de toutes les transactions.

Les compteurs OSM historiques non documentés sont exclus des graphiques,
même lorsque leur valeur est positive. Les données DVF absentes et les relevés
d'air non exploitables restent absents. Les graphiques utilisent les mêmes
métadonnées liées aux lignes Supabase que les fiches de la carte.

## Vérifications

`node tests/frontend-integrity.cjs` contrôle les liens entre données et
métadonnées. `node tests/dashboard-integrity.cjs` vérifie les couvertures de
l'audit, l'exclusion des manquants, les filtres, les médianes, les rendus des
sept modules et les sélections vides. Les contrôles visuels couvrent desktop et
mobile, ainsi que les sélecteurs et la réinitialisation du dashboard.

## Mise à jour des services par ville

La carte et les graphiques sont regroupés sous « Découvrir les villes ».
Le menu ne contient plus d'entrée séparée Dashboard KPI.
Les services sont désormais comptés à l'intérieur de la limite administrative
OSM de niveau 8 identifiée par le code INSEE. Les anciens comptages à 1 km
ne sont jamais utilisés comme totaux communaux, même si leur valeur est positive.
Les nombres restent des objets référencés dans OpenStreetMap ; la complétude
peut varier et les doublons de représentation restent possibles. Un total
communal ne mesure pas à lui seul l'accessibilité depuis chaque quartier.

## Présentation du portfolio

« Sources & méthode » présente le projet comme une étude de cas : question
de départ, collecte, préparation, contrôles, restitution et outils utilisés.
La rubrique se lit avec le défilement normal de la page. Les cartes de sources
décrivent les fichiers CSV ou les API utilisés et les limites principales.
Les filtres DVF précis et le rapport de contrôle restent accessibles dans des
blocs dépliables. Les fiches de villes et les commentaires des graphiques
utilisent des explications courtes plutôt que les messages techniques bruts.

La section de contact est en fin de rubrique. Son lien est configuré par
`PORTFOLIO_LINKEDIN_URL` dans `web/app.js`. Le bouton reste masqué tant
qu'une URL HTTPS de profil LinkedIn n'est pas renseignée.
