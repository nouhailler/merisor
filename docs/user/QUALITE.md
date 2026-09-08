# Analyser la qualité d'un MCD

Ouvrez **Modèle → Analyser la qualité du modèle…** (`Ctrl+Shift+Q`). Cette
analyse locale ne modifie jamais le MCD et n'appelle aucun service d'IA.

## Trois natures de constats

MERISOR sépare volontairement les résultats :

- **Erreur** : règle structurelle déterministe non respectée, par exemple une
  entité sans identifiant ou une relation sans cardinalité ;
- **Risque** : signal heuristique à examiner dans le contexte métier, par
  exemple un nom ambigu, deux entités proches ou un groupe répétitif ;
- **Suggestion** : amélioration facultative, par exemple utiliser `DATE` pour
  `date_naissance` ou ajouter `UNIQUE` à `email`.

Une erreur peut bloquer une transformation. Un risque ou une suggestion ne le
fait pas et ne doit jamais être appliqué sans décision humaine.

## Indicateur sur 100

Le score est un **indicateur heuristique, pas une certification**. Il combine
six dimensions pondérées : structure MERISE, identifiants, cardinalités,
typage, cohérence sémantique, normalisation et nommage. Le rapport affiche le
poids de chaque dimension et chaque retrait de points.

Un score élevé ne prouve ni la justesse du besoin métier, ni le respect formel
de toutes les formes normales. Inversement, un score plus faible peut refléter
un choix métier parfaitement volontaire. Le score sert à organiser une revue,
pas à remplacer l'analyste.

## Limites

Les signaux reposent sur la structure et les noms du modèle. MERISOR peut
reconnaître certains termes fréquents, mais il ne connaît pas le vocabulaire de
votre organisation. Utilisez l'assistant de normalisation pour l'analyse
formelle fondée sur les dépendances fonctionnelles, et la validation MCD pour
les erreurs structurelles.

