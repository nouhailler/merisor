# Espace SQL — UX 2.0

## Objectif

L’espace SQL est une étape de production explicite, alimentée exclusivement par
le MLD courant. Il ne reconstruit aucune règle depuis le MCD.

## Structure

- choix visible du dialecte PostgreSQL, SQLite ou MariaDB/MySQL ;
- état de validation et compte des tables/contraintes ;
- aperçu monospace avec numéros de lignes et coloration syntaxique légère ;
- recherche dans le script ;
- copie et export `.sql`.

Une modification du MCD rend le MLD obsolète et désactive l’accès à la
production SQL jusqu’à régénération.

## Fichiers

- `src/merisor/ui/sql_workspace.py`
- `src/merisor/ui/main_window.py`
- `tests/test_sql_workspace.py`

## Validation de phase

- génération et changement de dialecte ;
- validation bloquante lisible ;
- numéros de lignes, recherche, copie et export ;
- navigation de workflow vers l’espace intégré.

```text
PHASE : 9 — SQL
État : terminé

Fichiers créés :
- src/merisor/ui/sql_workspace.py
- tests/test_sql_workspace.py
- docs/SQL_WORKSPACE_UX.md

Fonctionnalités implémentées :
- espace SQL intégré et fondé uniquement sur le MLD
- dialectes, validation, statistiques, recherche, copie et export
- éditeur monospace numéroté avec coloration légère

Régressions détectées : aucune
Prochaine phase : PHASE 10 — IA
```
