from pathlib import Path

from PySide6.QtGui import QImage

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_application_logo_and_debian_icon_are_valid_png_files() -> None:
    application_logo = PROJECT_ROOT / "src/merisor/assets/merisor.png"
    debian_icon = (
        PROJECT_ROOT / "packaging/deb/usr/share/icons/hicolor/256x256/apps/merisor.png"
    )

    logo_image = QImage(str(application_logo))
    icon_image = QImage(str(debian_icon))

    assert not logo_image.isNull()
    assert logo_image.hasAlphaChannel()
    assert not icon_image.isNull()
    assert (icon_image.width(), icon_image.height()) == (256, 256)


def test_desktop_entry_uses_the_packaged_icon() -> None:
    desktop_entry = (
        PROJECT_ROOT / "packaging/deb/usr/share/applications/merisor.desktop"
    ).read_text(encoding="utf-8")

    assert "Icon=merisor\n" in desktop_entry

    appimage_desktop_entry = (
        PROJECT_ROOT / "packaging/appimage/io.github.nouhailler.merisor.desktop"
    ).read_text(encoding="utf-8")
    assert "Exec=merisor\n" in appimage_desktop_entry
    assert "Icon=merisor\n" in appimage_desktop_entry


def test_appimage_packaging_contains_required_desktop_metadata() -> None:
    app_run = PROJECT_ROOT / "packaging/appimage/AppRun"
    metadata = (
        PROJECT_ROOT / "packaging/appimage/io.github.nouhailler.merisor.appdata.xml"
    ).read_text(encoding="utf-8")
    build_script = PROJECT_ROOT / "packaging/build_appimage.sh"

    assert app_run.read_text(encoding="utf-8").startswith("#!/bin/sh\n")
    assert "<id>io.github.nouhailler.merisor</id>" in metadata
    assert "<project_license>MIT</project_license>" in metadata
    assert build_script.stat().st_mode & 0o111


def test_release_workflow_publishes_deb_and_appimage() -> None:
    workflow = (PROJECT_ROOT / ".github/workflows/release.yml").read_text(
        encoding="utf-8"
    )

    assert "./packaging/build_deb.sh" in workflow
    assert "./packaging/build_appimage.sh" in workflow
    assert "dist/*.deb" in workflow
    assert "dist/*.AppImage" in workflow


def test_readme_screenshots_are_present_and_readable() -> None:
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")

    for filename in (
        "mcd-editor.png",
        "attribute-types.png",
        "mld-view.png",
        "sql-preview.png",
        "ai-preview.png",
    ):
        relative_path = f"docs/images/{filename}"
        image = QImage(str(PROJECT_ROOT / relative_path))
        assert relative_path in readme
        assert not image.isNull()
        assert image.width() >= 900


def test_project_is_distributed_under_the_mit_license() -> None:
    license_text = (PROJECT_ROOT / "LICENSE").read_text(encoding="utf-8")

    assert license_text.startswith("MIT License\n")
    assert "Copyright (c) 2026 Nouhailler" in license_text
