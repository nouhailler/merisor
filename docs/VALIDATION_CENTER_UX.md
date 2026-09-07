# Centre de validation — expérience 2.0

Le centre de validation présente le `ValidationReport` existant. Il n'ajoute ni ne
duplique aucune règle métier.

Il distingue erreurs bloquantes, avertissements et contrôles réussis, propose un
filtre, détaille le code de contrôle et explique la famille de règle effectivement
exécutée. `Localiser` et `Corriger dans les propriétés` sélectionnent l'objet,
recentrent le canvas et rouvrent son inspecteur. Les problèmes globaux restent
consultables même lorsqu'aucun item graphique ne peut être ciblé.

## Rapport de PHASE 6

```text
PHASE : 6 — Validation Center
État : terminé

Fichiers créés :
- src/merisor/ui/validation_center.py
- tests/test_validation_center.py
- docs/VALIDATION_CENTER_UX.md

Fichiers modifiés :
- src/merisor/application/controller.py
- src/merisor/ui/main_window.py

Fonctionnalités implémentées :
- centre de validation intégré
- compteurs erreurs/avertissements/contrôles
- filtres et détails pédagogiques
- localisation, centrage et sélection automatiques
- explications Pourquoi ? fondées sur les contrôles réels

Tests exécutés :
- tests du centre et du focus canvas
- suite complète de qualité et de non-régression

Régressions détectées :
- aucune

Prochaine phase :
- PHASE 7 — Navigation MCD / MLD / SQL
```
