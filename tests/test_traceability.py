from __future__ import annotations

from typing import Any

from PySide6.QtTest import QSignalSpy

from merisor.application import McdToMldTransformer, ModelTraceabilityService, SQLTarget
from merisor.domain import (
    Association,
    Attribute,
    Cardinality,
    Entity,
    MCDModel,
    MLDModel,
)
from merisor.ui.mld_properties_panel import MLDPropertiesPanel
from merisor.ui.traceability_dialog import TraceabilityDialog


def _order_model() -> tuple[MCDModel, MLDModel]:
    model = MCDModel()
    client = Entity(
        "CLIENT",
        id="entity.client",
        attributes=[
            Attribute("id_client", True, id="attribute.client.id"),
            Attribute("nom", id="attribute.client.name"),
        ],
    )
    order = Entity(
        "COMMANDE",
        id="entity.order",
        attributes=[Attribute("id_commande", True, id="attribute.order.id")],
    )
    association = Association("PASSER", id="association.place")
    model.add_entity(client)
    model.add_entity(order)
    model.add_association(association)
    model.create_relation(client.id, association.id, Cardinality("0", "N"))
    model.create_relation(order.id, association.id, Cardinality("1", "1"))
    return model, McdToMldTransformer().transform(model)


def test_traces_migrated_fk_from_mcd_to_postgresql() -> None:
    mcd, mld = _order_model()
    table = mld.table("COMMANDE")
    column = table.column("id_client")

    report = ModelTraceabilityService().trace(
        mcd, mld, table, column.id, SQLTarget.POSTGRESQL
    )

    assert report.mcd_path == ("Entité CLIENT", "id_client")
    assert report.mld_path == ("COMMANDE", "id_client")
    assert "MCD → CLIENT.id_client" in report.origin
    assert "Association PASSER" in report.transformation
    assert "CLIENT (0,N)" in report.transformation
    assert "COMMANDE (1,1)" in report.transformation
    assert "création d'une FK dans COMMANDE vers CLIENT" in report.consequence
    assert 'FOREIGN KEY ("id_client") REFERENCES "CLIENT" ("id_client")' in report.sql


def test_trace_sql_uses_the_selected_dialect() -> None:
    mcd, mld = _order_model()
    table = mld.table("COMMANDE")
    column = table.column("id_client")

    report = ModelTraceabilityService().trace(
        mcd, mld, table, column.id, SQLTarget.MYSQL
    )

    quote = chr(96)
    assert report.sql_target is SQLTarget.MYSQL
    assert f"{quote}id_client{quote} INT" in report.sql
    assert f"REFERENCES {quote}CLIENT{quote} ({quote}id_client{quote})" in report.sql


def test_mld_panel_requests_the_selected_column_trace(qapp: Any) -> None:
    _mcd, mld = _order_model()
    table = mld.table("COMMANDE")
    panel = MLDPropertiesPanel()
    spy = QSignalSpy(panel.trace_requested)
    panel.display(table)
    item = panel.columns.topLevelItem(1)
    assert item is not None
    panel.columns.setCurrentItem(item)

    panel.why_button.click()

    assert spy.count() == 1
    assert spy.at(0)[0] is table
    assert spy.at(0)[1] == table.column("id_client").id


def test_traceability_dialog_navigates_and_switches_dialect(qapp: Any) -> None:
    mcd, mld = _order_model()
    table = mld.table("COMMANDE")
    dialog = TraceabilityDialog(mcd, mld, table, table.column("id_client").id)

    assert dialog.navigation.topLevelItemCount() == 3
    assert dialog.report is not None
    assert dialog.report.target_label == "COMMANDE.id_client"
    assert "TRANSFORMATION" in dialog.details.toPlainText()

    dialog.target_combo.setCurrentIndex(
        dialog.target_combo.findData(SQLTarget.SQLITE.value)
    )

    assert dialog.report is not None
    assert dialog.report.sql_target is SQLTarget.SQLITE
    sql_root = dialog.navigation.topLevelItem(2)
    assert sql_root is not None
    dialog.navigation.setCurrentItem(sql_root)
    assert "SQL — SQLite" in dialog.details.toPlainText()
