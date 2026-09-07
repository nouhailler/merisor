# Centre de documentation — UX 2.0

## Usage

La documentation hors ligne est désormais un espace du flux principal. Le
raccourci `F1` et le menu **Documentation** ouvrent la rubrique demandée sans
masquer le contexte de l’application.

Le centre comprend :

- une arborescence par public et par sujet ;
- une recherche instantanée des rubriques ;
- un lecteur Markdown ;
- des liens internes et un accès optionnel à la documentation GitHub.

Le lecteur modal historique reste disponible comme composant compatible.

## Fichiers

- `src/merisor/ui/documentation_dialog.py`
- `src/merisor/ui/main_window.py`
- `src/merisor/application/documentation_catalog.py`
- `tests/test_documentation.py`

```text
PHASE : 11 — Documentation
État : terminé

Fonctionnalités implémentées :
- centre de documentation intégré
- F1 et liens ciblés vers les rubriques
- navigation, recherche et lecture Markdown hors ligne
- adaptateur modal conservé pour compatibilité

Régressions détectées : aucune
Prochaine phase : PHASE 12 — Finitions et tests
```
