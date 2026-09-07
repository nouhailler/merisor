from __future__ import annotations

from PySide6.QtGui import QAction

from merisor.application.documentation_catalog import DocumentationCatalog
from merisor.domain import MCDModel, Position
from merisor.ui.command_palette import CommandPalette, GlobalSearchDialog


def test_command_palette_filters_and_triggers_action(qapp) -> None:  # type: ignore[no-untyped-def]
    called: list[bool] = []
    validate = QAction("Valider le MCD")
    validate.triggered.connect(lambda: called.append(True))
    other = QAction("Exporter")
    palette = CommandPalette((validate, other))

    palette.search.setText("valid")
    assert palette.results.count() == 1
    palette.results.item(0).setSelected(True)
    palette.results.itemActivated.emit(palette.results.item(0))
    assert called == [True]


def test_global_search_indexes_model_mld_and_documentation(qapp, tmp_path) -> None:  # type: ignore[no-untyped-def]
    mcd = MCDModel()
    entity = mcd.create_entity("CLIENT", Position())
    mcd.create_attribute(entity.id, "email")
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "INDEX.md").write_text("# Documentation", encoding="utf-8")
    catalog = DocumentationCatalog(docs)
    dialog = GlobalSearchDialog(mcd, None, catalog=catalog)

    dialog.search.setText("email")
    assert dialog.results.count() == 1
    assert "Attribut de CLIENT" in dialog.results.item(0).text()
    selected: list[tuple[str, str]] = []
    dialog.result_requested.connect(
        lambda kind, item_id: selected.append((kind, item_id))
    )
    dialog.results.itemActivated.emit(dialog.results.item(0))
    assert selected == [("mcd", entity.id)]
