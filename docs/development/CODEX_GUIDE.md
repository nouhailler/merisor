# Guide de reprise pour Codex

[← Portail](../INDEX.md) · [Architecture](../technical/ARCHITECTURE.md)

## Avant toute modification

1. lire `README.md` ;
2. lire `CONTEXT.md` et `docs/decisions/CONTEXT.md` ;
3. lire les ADR et `technical/ARCHITECTURE.md` ;
4. inspecter les modules concernés ;
5. lire les tests existants ;
6. préserver les modifications utilisateur non liées.

## Contraintes permanentes

- ne pas casser le JSON V1/V2 ;
- ne pas contourner `DiagramController` pour une mutation UI ;
- ne pas placer la logique métier dans Qt ;
- conserver MCD → MLD → SQL ;
- ne jamais exécuter un SQL ;
- ne jamais enregistrer une clé API ;
- valider et prévisualiser toute sortie IA/import ;
- garder les opérations importantes annulables ;
- ajouter des tests à toute nouvelle règle.

## Méthode

Pour une évolution métier : domaine, service applicatif, tests unitaires,
contrôleur/commande, UI, tests intégration, documentation. Vérifier les états
incomplets autorisés et les migrations.

## Fin de tâche

Exécuter :

```bash
ruff format --check .
ruff check .
mypy
QT_QPA_PLATFORM=offscreen pytest
QT_QPA_PLATFORM=offscreen timeout 5s python -m merisor
```

Rapporter fichiers, décisions, tests et limitations. Ne pas commencer une
version suivante sans demande.
