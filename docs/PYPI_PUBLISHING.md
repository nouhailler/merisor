# Publication de MERISOR sur PyPI

Le workflow `.github/workflows/release.yml` construit automatiquement :

- `merisor-<version>-py3-none-any.whl` ;
- `merisor-<version>.tar.gz` ;
- le paquet Debian et l'AppImage de la même version.

La publication utilise **Trusted Publishing** (OIDC). Aucun mot de passe ni
jeton PyPI ne doit être ajouté aux secrets GitHub.

## Configuration initiale du compte PyPI

Cette opération doit être réalisée une seule fois par le propriétaire du compte
PyPI :

1. se connecter à <https://pypi.org/> et activer l'authentification à deux
   facteurs ;
2. ouvrir <https://pypi.org/manage/account/publishing/> ;
3. créer un **pending publisher** avec les valeurs exactes suivantes :

   | Champ PyPI | Valeur |
   |---|---|
   | PyPI project name | `merisor` |
   | Owner | `nouhailler` |
   | Repository name | `merisor` |
   | Workflow name | `release.yml` |
   | Environment name | `pypi` |

4. dans GitHub, créer si souhaité l'environnement `pypi` et lui ajouter une
   règle d'approbation manuelle.

Le nom `merisor` était disponible lors de la mise en place de ce workflow. Le
pending publisher réservera le projet et autorisera sa première publication.

## Publier une version

La version n'est définie qu'à un seul endroit : `src/merisor/__init__.py`.
Après validation de la suite de tests :

```bash
git tag -a v0.6.0 -m "MERISOR 0.6.0"
git push origin v0.6.0
```

Le tag doit impérativement correspondre à `v` suivi de `__version__`. Le
workflow refuse toute incohérence afin d'éviter une mauvaise publication.

Une version PyPI ne peut jamais être remplacée. Toute correction exige donc un
nouveau numéro de version.

## Vérification locale avant publication

```bash
python -m pip install --upgrade build twine
python -m build
python -m twine check dist/*
pipx install --force dist/merisor-*-py3-none-any.whl
merisor
```
