# Inspecteur de propriétés — expérience 2.0

Le panneau droit reste connecté au contrôleur et ne modifie jamais directement le
modèle métier.

## États contextuels

- aucune sélection : synthèse du MCD (entités, associations, attributs, relations
  et état de validation) ;
- sélection multiple : nombre d'objets et rappel des actions groupées ;
- entité ou association : général, attributs, propriétés complètes et options de
  transformation pertinentes ;
- relation : extrémités, rôle et cardinalité accompagnés d'une explication ;
- table MLD : inspecteur en lecture seule existant.

Les attributs conservent toutes leurs capacités : identifiant, type, taille,
précision, échelle, nullabilité, défaut, unicité, auto-incrémentation, commentaire,
contraintes et analyse d'impact. L'action d'application est primaire et la
suppression utilise le rôle visuel danger.

## Rapport de PHASE 5

```text
PHASE : 5 — Properties Panel
État : terminé

Fichiers créés :
- docs/PROPERTIES_PANEL_UX.md

Fichiers modifiés :
- src/merisor/ui/properties_panel.py
- tests/test_qt_integration.py

Fonctionnalités implémentées :
- résumé du modèle sans sélection
- état explicite de sélection multiple
- sections Général, Attributs et Transformation
- formulaire de relation pédagogique
- hiérarchie des actions primaire/destructive

Tests exécutés :
- tests Qt du panneau et des éditions annulables
- suite complète de qualité et de non-régression

Régressions détectées :
- aucune

Prochaine phase :
- PHASE 6 — Validation Center
```
