import re
from pathlib import Path

import pytest

from merisor.application.documentation_catalog import (
    DOCUMENTATION_PAGES,
    DocumentationCatalog,
    DocumentationError,
)
from merisor.persistence import JsonDiagramRepository
from merisor.ui.documentation_dialog import DocumentationDialog
from merisor.ui.main_window import MainWindow

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOCS_ROOT = PROJECT_ROOT / "docs"
MARKDOWN_LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")


def test_documentation_catalog_references_existing_unique_pages() -> None:
    catalog = DocumentationCatalog(DOCS_ROOT)

    assert catalog.root == DOCS_ROOT.resolve()
    assert len({page.id for page in DOCUMENTATION_PAGES}) == len(DOCUMENTATION_PAGES)
    assert len({page.relative_path for page in DOCUMENTATION_PAGES}) == len(
        DOCUMENTATION_PAGES
    )
    for page in catalog.pages:
        path = catalog.path(page.id)
        assert path.is_file()
        assert path.read_text(encoding="utf-8").startswith("# ")
        assert catalog.page_id_for_path(path) == page.id


def test_documentation_catalog_reports_unknown_or_missing_pages(tmp_path: Path) -> None:
    catalog = DocumentationCatalog(DOCS_ROOT)
    with pytest.raises(DocumentationError, match="inconnue"):
        catalog.path("missing")

    empty_catalog = DocumentationCatalog(tmp_path)
    with pytest.raises(DocumentationError, match="introuvable"):
        _ = empty_catalog.root


def test_internal_documentation_links_resolve() -> None:
    for source in DOCS_ROOT.rglob("*.md"):
        for destination in MARKDOWN_LINK.findall(source.read_text(encoding="utf-8")):
            target = destination.split("#", maxsplit=1)[0].strip("<>")
            if not target or "://" in target or target.startswith("mailto:"):
                continue
            resolved = (source.parent / target).resolve()
            assert resolved.exists(), f"Lien cassé dans {source}: {destination}"


def test_motogp_example_is_a_valid_merisor_project() -> None:
    model = JsonDiagramRepository().load(PROJECT_ROOT / "examples/motogp.json")

    assert {entity.name for entity in model.entities.values()} == {"PILOTE", "EQUIPE"}
    association = next(iter(model.associations.values()))
    assert association.name == "ENGAGER"
    assert association.is_historized
    assert len(model.relations) == 2


def test_documentation_dialog_reads_and_filters_local_manual(qapp: object) -> None:
    dialog = DocumentationDialog(
        "getting-started", catalog=DocumentationCatalog(DOCS_ROOT)
    )

    assert dialog.windowTitle() == "Documentation MERISOR"
    assert "Prise en main" in dialog.browser.toPlainText()
    dialog.search.setText("Cardinalités")
    visible_pages = []
    root = dialog.navigation.invisibleRootItem()
    for category_index in range(root.childCount()):
        category = root.child(category_index)
        if category is None:
            continue
        for page_index in range(category.childCount()):
            page = category.child(page_index)
            if page is not None and not page.isHidden():
                visible_pages.append(page.text(0))

    assert visible_pages == ["Cardinalités"]
    dialog.close()


def test_main_window_exposes_documentation_menu_and_f1(qapp: object) -> None:
    window = MainWindow()

    menus = [action.text() for action in window.menuBar().actions()]
    assert "Documentation" in menus
    assert window.documentation_action.shortcut().toString() == "F1"
    assert window.documentation_action.isEnabled()
    window.close()


def test_installable_packages_include_offline_documentation() -> None:
    pyproject = (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    spec = (PROJECT_ROOT / "packaging/merisor.spec").read_text(encoding="utf-8")
    deb_script = (PROJECT_ROOT / "packaging/build_deb.sh").read_text(encoding="utf-8")

    assert '"share/doc/merisor/user"' in pyproject
    assert '"share/doc/merisor/decisions/ADR"' in pyproject
    assert '(str(project_root / "docs"), "docs")' in spec
    assert 'cp -a "$project_root/docs/."' in deb_script


def test_readme_is_a_short_discovery_page_linking_to_the_manual() -> None:
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")

    assert len(readme.splitlines()) < 400
    assert "docs/INDEX.md" in readme
    assert "Documentation" in readme
