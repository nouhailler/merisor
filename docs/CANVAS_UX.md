# Canvas MCD — expérience 2.0

## Principes visuels

Le canvas reste une projection du `MCDModel` synchronisée par
`DiagramController`. La phase 4 ne modifie ni la structure métier, ni les
positions sauvegardées, ni la création des relations.

Les entités utilisent désormais une carte à hiérarchie forte : bandeau de titre,
accent de marque, colonnes nom/type et badge textuel `PK`. L'identifiant n'est donc
plus indiqué par la seule couleur. Les associations conservent le losange MERISE
et affichent leurs attributs dans un panneau aligné.

La sélection combine bordure primaire et poignées visibles. Le survol renforce la
bordure des nœuds et relations. Les cardinalités utilisent une surface adaptée au
thème afin de rester lisibles au-dessus des liens.

## Interactions

- molette : zoom sous le pointeur ;
- bouton central : déplacement panoramique ;
- `Espace` + glisser gauche : déplacement panoramique alternatif ;
- glisser dans le vide : sélection rectangulaire ;
- `Ctrl+C`, `Ctrl+V`, `Ctrl+D` : copier, coller, dupliquer ;
- grille, aimantation, guides et zoom restent accessibles dans la palette ;
- recherche visuelle : les non-correspondances sont atténuées ;
- minimap : navigation et indication de la zone visible ;
- auto-layout : commande existante, toujours annulable.

Les associations réflexives restent différenciées par leurs rôles de branche et
les branches parallèles ; les associations n-aires convergent explicitement vers
le même losange. La représentation ne masque donc pas leur degré.

## Rapport de PHASE 4

```text
PHASE : 4 — Canvas MCD
État : terminé

Fichiers créés :
- docs/CANVAS_UX.md

Fichiers modifiés :
- src/merisor/ui/items.py
- src/merisor/ui/canvas.py
- src/merisor/ui/main_window.py
- src/merisor/application/controller.py
- tests/test_canvas_productivity.py

Fonctionnalités implémentées :
- cartes d'entité modernes avec badge PK et types alignés
- associations et attributs plus lisibles
- états survol/sélection et poignées visuelles
- cardinalités et ISA adaptés aux thèmes
- pan avec Espace + glisser
- accès regroupé aux outils du canvas

Tests exécutés :
- tests des interactions et représentations canvas
- suite complète de qualité et de non-régression

Régressions détectées :
- aucune

Prochaine phase :
- PHASE 5 — Properties Panel
```
