# Packaging Linux

[← Portail](../INDEX.md) · [Release](RELEASE.md)

## Paquet Debian

```bash
./packaging/build_deb.sh
dpkg-deb --info dist/merisor_*.deb
```

Le paquet installe l'application sous `/usr/lib/merisor`, le lanceur, l'entrée
desktop, l'icône, la licence et la documentation sous
`/usr/share/doc/merisor`.

## AppImage

```bash
python -m pip install -e ".[ai]" pyinstaller
./packaging/build_appimage.sh
./dist/MERISOR-*-x86_64.AppImage
```

`packaging/merisor.spec` collecte code, icône, keyring éventuel et documentation.
Le script prend en charge `x86_64` et `aarch64`, prépare l'AppDir puis utilise
une version épinglée d'appimagetool.

## Wheel / PyPI

Les `data-files` setuptools installent les pages sous
`share/doc/merisor`. Vérifiez le contenu :

```bash
python -m build
python -m zipfile -l dist/merisor-*.whl
```

## Smoke tests

```bash
timeout 5s dist/*.AppImage
sudo apt install ./dist/merisor_*.deb
merisor
```

Le menu **Documentation** doit trouver les pages dans les sources, le préfixe
d'installation ou le répertoire temporaire PyInstaller.
