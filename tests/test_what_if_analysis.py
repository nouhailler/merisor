from __future__ import annotations

import copy

from merisor.application import ImpactLayer, WhatIfAnalyzer
from merisor.domain import Association, Attribute, Cardinality, Entity, MCDModel
from merisor.ui.main_window import MainWindow
from merisor.ui.what_if_dialog import WhatIfImpactDialog


def client_model() -> tuple[MCDModel, Attribute, Attribute]:
    model = MCDModel()
    identifier = Attribute("id_client", True, id="client-id")
    email = Attribute("email", id="client-email", unique=True)
    model.add_entity(Entity("CLIENT", id="client", attributes=[identifier, email]))
    return model, identifier, email


def test_delete_attribute_traces_mcd_mld_sql_and_generated_outputs() -> None:
    model, _identifier, email = client_model()
    before = copy.deepcopy(model)

    report = WhatIfAnalyzer().analyze_delete(model, email.id)

    assert report.target.label == "CLIENT.email"
    assert any(
        item.label == "CLIENT.email" for item in report.for_layer(ImpactLayer.MCD)
    )
    assert any(
        item.label == "CLIENT.email" for item in report.for_layer(ImpactLayer.MLD)
    )
    sql_labels = {item.label for item in report.for_layer(ImpactLayer.SQL)}
    assert "Colonne CLIENT.email" in sql_labels
    assert "UNIQUE(email)" in sql_labels
    assert report.for_layer(ImpactLayer.DOCUMENTATION)
    assert report.for_layer(ImpactLayer.TEST_DATA)
    assert report.for_layer(ImpactLayer.QUERIES)
    assert not report.new_validation_errors
    assert model.entities == before.entities


def test_simulation_detects_new_validation_errors() -> None:
    model, identifier, _email = client_model()

    report = WhatIfAnalyzer().analyze_delete(model, identifier.id)

    assert any(
        "aucun identifiant" in message for message in report.new_validation_errors
    )


def test_delete_entity_simulates_relation_and_table_removal_without_mutation() -> None:
    model, _identifier, _email = client_model()
    order = Entity(
        "COMMANDE",
        id="order",
        attributes=[Attribute("id_commande", True, id="order-id")],
    )
    association = Association("PASSER", id="place-order")
    model.add_entity(order)
    model.add_association(association)
    relation = model.create_relation(
        "client",
        association.id,
        Cardinality("0", "N"),
    )
    model.create_relation(
        order.id,
        association.id,
        Cardinality("1", "1"),
    )

    report = WhatIfAnalyzer().analyze_delete(model, "client")

    assert any(
        item.label == "CLIENT ↔ PASSER" for item in report.for_layer(ImpactLayer.MCD)
    )
    assert any(
        item.label == "CLIENT.id_client" for item in report.for_layer(ImpactLayer.MLD)
    )
    assert relation.id in model.relations
    assert "client" in model.entities


def test_confirmed_attribute_deletion_is_undoable(qapp) -> None:  # type: ignore[no-untyped-def]
    model, _identifier, email = client_model()
    window = MainWindow()
    window.controller.load_transient_model(model)

    window.controller.delete_element(email.id)
    assert [
        item.name for item in window.controller.model.entities["client"].attributes
    ] == ["id_client"]
    assert window.controller.undo_stack.undoText() == "Supprimer un attribut"

    window.controller.undo_stack.undo()
    assert [
        item.name for item in window.controller.model.entities["client"].attributes
    ] == [
        "id_client",
        "email",
    ]
    window.controller.undo_stack.setClean()
    window.close()


def test_what_if_dialog_previews_without_applying(qapp) -> None:  # type: ignore[no-untyped-def]
    model, _identifier, email = client_model()
    dialog = WhatIfImpactDialog(model, email.id)

    assert dialog.target_id == email.id
    assert dialog.tree.topLevelItemCount() == len(ImpactLayer)
    assert "Aucune modification" in dialog.summary_label.text()
    assert dialog.continue_button.text() == "Continuer et supprimer"
    assert len(model.entities["client"].attributes) == 2
    dialog.close()


def test_main_window_exposes_what_if_action(qapp) -> None:  # type: ignore[no-untyped-def]
    window = MainWindow()

    assert window.impact_analysis_action.text().startswith("Et si… ?")
    assert window.impact_analysis_action.shortcut().toString()
    assert window.properties_panel.analyze_attribute_impact_button.text().startswith(
        "Et si"
    )

    window.controller.undo_stack.setClean()
    window.close()
