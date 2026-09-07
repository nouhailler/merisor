# Assistant IA — UX 2.0

## Point d’entrée unique

Le hub **✨ Assistant MERISOR** regroupe les usages existants :

- conception conversationnelle ;
- génération d’un MCD depuis une description ;
- analyse et réparation assistées ;
- analyse locale de qualité ;
- normalisation ;
- explication du MLD.

## Parcours de confiance

Les opérations génératives suivent : demande → proposition → prévisualisation →
validation locale → diff → confirmation → modification. Les appels OpenRouter
restent asynchrones afin de ne pas bloquer l’interface.

La clé OpenRouter est conservée hors du JSON du projet. Elle n’est jamais
incluse dans le MCD, le MLD, le SQL ni les journaux.

## Fichiers

- `src/merisor/ui/ai_hub.py`
- `src/merisor/ui/main_window.py`
- `tests/test_ai_hub.py`

```text
PHASE : 10 — IA
État : terminé

Fonctionnalités implémentées :
- point d'entrée unifié des assistants
- sécurité et confirmation rendues visibles
- conservation des traitements OpenRouter asynchrones existants
- accès direct à la qualité, normalisation et explication

Régressions détectées : aucune
Prochaine phase : PHASE 11 — Documentation
```
