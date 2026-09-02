# Publier une version

[← Portail](../INDEX.md) · [Packaging](PACKAGING.md)

## Préparation

1. vérifier que `main` est propre et à jour ;
2. mettre à jour `src/merisor/__init__.py` ;
3. compléter `CHANGELOG.md` avec version et date ;
4. vérifier README, documentation et exemples ;
5. exécuter format, lint, mypy, tests et smoke test ;
6. construire localement les paquets si possible.

## Tag

```bash
git tag -a vX.Y.Z -m "MERISOR X.Y.Z"
git push origin main
git push origin vX.Y.Z
```

Le workflow `.github/workflows/release.yml` construit le `.deb` et l'AppImage,
effectue un smoke test puis crée la release GitHub pour les tags `v*`.

## Vérifications après publication

- page GitHub Releases et sommes/taille des artefacts ;
- installation du `.deb` sur Debian/Ubuntu ;
- exécution de l'AppImage ;
- version affichée dans l'application ;
- documentation locale dans les deux paquets ;
- publication PyPI si la version doit être disponible par `pipx`.

## PyPI

La procédure et les secrets nécessaires sont détaillés dans
[PYPI_PUBLISHING.md](../PYPI_PUBLISHING.md). Ne publiez jamais depuis un arbre
non testé.
