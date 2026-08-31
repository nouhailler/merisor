#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python_bin="${PYTHON:-python3}"
version="$(PYTHONPATH="$project_root/src" "$python_bin" -c 'from merisor import __version__; print(__version__)')"
machine="$(uname -m)"

case "$machine" in
    x86_64|amd64)
        appimage_arch="x86_64"
        ;;
    aarch64|arm64)
        appimage_arch="aarch64"
        ;;
    *)
        printf 'Architecture AppImage non prise en charge : %s\n' "$machine" >&2
        exit 1
        ;;
esac

if ! "$python_bin" -m PyInstaller --version >/dev/null 2>&1; then
    printf '%s\n' \
        "PyInstaller est requis. Installez les outils avec :" \
        "  $python_bin -m pip install -e \".[ai]\" pyinstaller" >&2
    exit 1
fi

output_dir="$project_root/dist"
output="$output_dir/MERISOR-${version}-${appimage_arch}.AppImage"
work_root="$(mktemp -d)"
appdir="$work_root/MERISOR.AppDir"
trap 'rm -rf "$work_root"' EXIT

"$python_bin" -m PyInstaller \
    --noconfirm \
    --clean \
    --workpath "$work_root/pyinstaller-build" \
    --distpath "$work_root/pyinstaller-dist" \
    "$project_root/packaging/merisor.spec"

mkdir -p \
    "$appdir/usr/bin" \
    "$appdir/usr/share/applications" \
    "$appdir/usr/share/icons/hicolor/256x256/apps" \
    "$appdir/usr/share/metainfo" \
    "$appdir/usr/share/doc/merisor"
cp -a "$work_root/pyinstaller-dist/merisor" "$appdir/usr/bin/merisor"
install -m 0755 "$project_root/packaging/appimage/AppRun" "$appdir/AppRun"
install -m 0644 \
    "$project_root/packaging/appimage/io.github.nouhailler.merisor.desktop" \
    "$appdir/io.github.nouhailler.merisor.desktop"
cp "$appdir/io.github.nouhailler.merisor.desktop" \
    "$appdir/usr/share/applications/io.github.nouhailler.merisor.desktop"
install -m 0644 \
    "$project_root/packaging/deb/usr/share/icons/hicolor/256x256/apps/merisor.png" \
    "$appdir/merisor.png"
cp "$appdir/merisor.png" \
    "$appdir/usr/share/icons/hicolor/256x256/apps/merisor.png"
install -m 0644 \
    "$project_root/packaging/appimage/io.github.nouhailler.merisor.appdata.xml" \
    "$appdir/usr/share/metainfo/io.github.nouhailler.merisor.appdata.xml"
install -m 0644 "$project_root/LICENSE" "$appdir/usr/share/doc/merisor/LICENSE"
ln -s merisor.png "$appdir/.DirIcon"

appimagetool="${APPIMAGETOOL:-$project_root/build/appimagetool-${appimage_arch}.AppImage}"
case "$appimage_arch" in
    x86_64)
        appimagetool_sha256="ed4ce84f0d9caff66f50bcca6ff6f35aae54ce8135408b3fa33abfc3cb384eb0"
        runtime_sha256="2fca8b443c92510f1483a883f60061ad09b46b978b2631c807cd873a47ec260d"
        ;;
    aarch64)
        appimagetool_sha256="f0837e7448a0c1e4e650a93bb3e85802546e60654ef287576f46c71c126a9158"
        runtime_sha256="00cbdfcf917cc6c0ff6d3347d59e0ca1f7f45a6df1a428a0d6d8a78664d87444"
        ;;
esac
if [[ ! -x "$appimagetool" ]]; then
    appimagetool_version="${APPIMAGETOOL_VERSION:-1.9.1}"
    mkdir -p "$(dirname "$appimagetool")"
    curl -L --fail --silent --show-error \
        "https://github.com/AppImage/appimagetool/releases/download/${appimagetool_version}/appimagetool-${appimage_arch}.AppImage" \
        -o "$appimagetool"
    chmod +x "$appimagetool"
fi
if [[ -z "${APPIMAGETOOL:-}" ]]; then
    printf '%s  %s\n' "$appimagetool_sha256" "$appimagetool" | sha256sum --check --status
fi

runtime="${APPIMAGE_RUNTIME:-$project_root/build/runtime-${appimage_arch}}"
if [[ ! -f "$runtime" ]]; then
    runtime_version="${APPIMAGE_RUNTIME_VERSION:-20251108}"
    mkdir -p "$(dirname "$runtime")"
    curl -L --fail --silent --show-error \
        "https://github.com/AppImage/type2-runtime/releases/download/${runtime_version}/runtime-${appimage_arch}" \
        -o "$runtime"
fi
if [[ -z "${APPIMAGE_RUNTIME:-}" ]]; then
    printf '%s  %s\n' "$runtime_sha256" "$runtime" | sha256sum --check --status
fi

mkdir -p "$output_dir"
if command -v appstreamcli >/dev/null 2>&1; then
    appstreamcli validate --no-net \
        "$appdir/usr/share/metainfo/io.github.nouhailler.merisor.appdata.xml"
fi
ARCH="$appimage_arch" APPIMAGE_EXTRACT_AND_RUN=1 \
    "$appimagetool" --no-appstream --runtime-file "$runtime" "$appdir" "$output"
chmod +x "$output"
printf 'AppImage créée : %s\n' "$output"
