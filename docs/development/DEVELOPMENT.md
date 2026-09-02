# Environnement développeur

[← Portail](../INDEX.md) · [Architecture](../technical/ARCHITECTURE.md)

## Prérequis

- Linux ;
- Python 3.10 ou plus récent ;
- Git ;
- module `venv` ;
- bibliothèques système Qt requises par la distribution.

## Installation

```bash
git clone https://github.com/nouhailler/merisor.git
cd merisor
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools
python -m pip install -e ".[test,ai,quality]"
python -m merisor
```

L'extra `ai` ajoute `keyring`; `quality` ajoute Ruff et mypy.

## Qualité

```bash
ruff format --check .
ruff check .
mypy
QT_QPA_PLATFORM=offscreen pytest
```

La CI exécute les mêmes commandes. Utilisez `ruff format .` pour appliquer le
formatage.

## Smoke test Qt

```bash
QT_QPA_PLATFORM=offscreen timeout 5s python -m merisor
```

Le code de sortie `124` indique ici que l'application est restée active jusqu'au
timeout, ce qui constitue le résultat attendu.

## Organisation d'une évolution

1. lire le contexte et les ADR ;
2. identifier le domaine et les tests existants ;
3. implémenter la règle sans Qt si possible ;
4. connecter le contrôleur puis l'interface ;
5. ajouter les tests unitaires, intégration et UI proportionnés ;
6. mettre à jour documentation et changelog.

Voir [Contribuer](CONTRIBUTING.md) et [Guide Codex](CODEX_GUIDE.md).
