# Navigation MCD → MLD → SQL

La barre de workflow expose l'état réel de chaque niveau :

```text
Concevoir → Vérifier → Transformer → Produire
```

Un symbole et une couleur sémantique distinguent prêt, avertissement, erreur et
résultat à régénérer. Le texte d'aide précise toujours la prochaine action. La
production reste désactivée tant qu'aucun MLD à jour n'existe.

Une tentative de transformation sur un MCD invalide ouvre directement le centre
de validation intégré. Une modification du MCD marque le MLD comme obsolète ; le
générateur SQL ne reçoit jamais ce résultat périmé.

## Rapport de PHASE 7

```text
PHASE : 7 — Navigation MCD / MLD / SQL
État : terminé

Fichiers créés :
- tests/test_workflow_navigation.py
- docs/WORKFLOW_NAVIGATION.md

Fichiers modifiés :
- src/merisor/ui/application_shell.py
- src/merisor/ui/main_window.py
- src/merisor/ui/theme/tokens.py
- tests/test_application_shell.py

Fonctionnalités implémentées :
- états explicites prêt/avertissement/erreur/obsolète
- production verrouillée sans MLD à jour
- redirection des transformations bloquées vers la validation
- conservation de la chaîne MCD → MLD → SQL

Tests exécutés :
- tests de navigation et d'obsolescence
- suite complète de qualité et de non-régression

Régressions détectées :
- aucune

Prochaine phase :
- PHASE 8 — MLD
```
