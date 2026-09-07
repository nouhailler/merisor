# Vue MLD — expérience 2.0

L'espace logique rassemble trois représentations du même `MLDModel` :

- **Graphique** : tables, colonnes, PK/FK/UQ/AI et dépendances ;
- **Texte** : représentation déterministe copiable et exportable ;
- **Provenance** : correspondance entre tables/colonnes et identifiants MCD
  sources.

Le placement graphique calcule la hauteur de chaque rangée à partir des tables
réelles, évitant le chevauchement des tables riches. Les couleurs suivent le thème
global. La sélection d'une table continue d'alimenter l'inspecteur et l'action
« Pourquoi ? » explique la transformation réelle.

## Rapport de PHASE 8

```text
PHASE : 8 — MLD
État : terminé

Fichiers créés :
- docs/MLD_VIEW_UX.md

Fichiers modifiés :
- src/merisor/ui/mld_view.py
- src/merisor/ui/main_window.py
- tests/test_mld_integration.py

Fonctionnalités implémentées :
- onglets Graphique, Texte et Provenance
- origine MCD des tables et colonnes
- placement vertical adapté au contenu
- rendu clair/sombre issu du design system
- statuts sans styles locaux

Tests exécutés :
- tests MLD, provenance, copie et export
- suite complète de qualité et de non-régression

Régressions détectées :
- aucune

Prochaine phase :
- PHASE 9 — SQL
```
