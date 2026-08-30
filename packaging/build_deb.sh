#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
version="$(PYTHONPATH="$project_root/src" python3 -c 'from merisor import __version__; print(__version__)')"
architecture="$(dpkg --print-architecture)"
package_name="merisor"
output_dir="$project_root/dist"
output="$output_dir/${package_name}_${version}_${architecture}.deb"
staging="$(mktemp -d)"
trap 'rm -rf "$staging"' EXIT

mkdir -p "$staging/usr/lib/merisor" "$staging/usr/bin" \
    "$staging/usr/share/applications" \
    "$staging/usr/share/icons/hicolor/256x256/apps" \
    "$staging/usr/share/doc/merisor"
cp -a "$project_root/src/merisor" "$staging/usr/lib/merisor/"
find "$staging/usr/lib/merisor" -type d -name __pycache__ -prune -exec rm -rf {} +
cp "$project_root/packaging/deb/usr/bin/merisor" "$staging/usr/bin/merisor"
cp "$project_root/packaging/deb/usr/share/applications/merisor.desktop" \
    "$staging/usr/share/applications/merisor.desktop"
cp "$project_root/packaging/deb/usr/share/icons/hicolor/256x256/apps/merisor.png" \
    "$staging/usr/share/icons/hicolor/256x256/apps/merisor.png"
cp "$project_root/LICENSE" "$staging/usr/share/doc/merisor/LICENSE"
sed "s/^Version:.*/Version: $version/; s/^Architecture:.*/Architecture: $architecture/" \
    "$project_root/packaging/deb/DEBIAN/control" > "$staging/control"
mkdir -p "$staging/DEBIAN"
mv "$staging/control" "$staging/DEBIAN/control"
mkdir -p "$output_dir"
dpkg-deb --build --root-owner-group "$staging" "$output"
printf 'Paquet créé : %s\n' "$output"
