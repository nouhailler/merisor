"""Configuration PyInstaller utilisée pour construire l'AppImage."""

from importlib.util import find_spec
from pathlib import Path


project_root = Path(SPEC).resolve().parent.parent
datas = [
    (
        str(project_root / "src/merisor/assets/merisor.png"),
        "merisor/assets",
    ),
    (str(project_root / "docs"), "docs"),
    (str(project_root / "examples"), "examples"),
]
binaries = []
hiddenimports = []

# L'import est dynamique dans MERISOR. Le hook officiel PyInstaller collecte
# ensuite uniquement les backends et métadonnées nécessaires de keyring.
if find_spec("keyring") is not None:
    hiddenimports.append("keyring")

analysis = Analysis(
    [str(project_root / "src/merisor/__main__.py")],
    pathex=[str(project_root / "src")],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
python_archive = PYZ(analysis.pure)

executable = EXE(
    python_archive,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="merisor",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
)

collection = COLLECT(
    executable,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="merisor",
)
