from __future__ import annotations

import copy

from merisor.application import (
    BusinessScenarioAnalyzer,
    ScenarioCheckStatus,
    parse_scenario,
)
from merisor.domain import Association, Attribute, Cardinality, Entity, MCDModel
from merisor.ui.business_scenario_dialog import BusinessScenarioDialog
from merisor.ui.main_window import MainWindow


def library_model() -> MCDModel:
    model = MCDModel()
    entities = (
        Entity(
            "LECTEUR",
            id="reader",
            attributes=[Attribute("id_lecteur", True, id="reader-id")],
        ),
        Entity(
            "EMPRUNT",
            id="loan",
            attributes=[
                Attribute("id_emprunt", True, id="loan-id"),
                Attribute("date_debut", id="start-date"),
                Attribute("date_retour", id="return-date"),
            ],
        ),
        Entity(
            "EXEMPLAIRE",
            id="copy",
            attributes=[Attribute("id_exemplaire", True, id="copy-id")],
        ),
        Entity(
            "LIVRE",
            id="book",
            attributes=[Attribute("id_livre", True, id="book-id")],
        ),
    )
    for entity in entities:
        model.add_entity(entity)
    associations = (
        Association("EFFECTUER", id="perform"),
        Association("CONCERNER", id="concern"),
        Association("REPRÉSENTER", id="represent"),
    )
    for association in associations:
        model.add_association(association)
    for entity_id, association_id, cardinality in (
        ("reader", "perform", Cardinality("0", "N")),
        ("loan", "perform", Cardinality("1", "1")),
        ("copy", "concern", Cardinality("0", "N")),
        ("loan", "concern", Cardinality("1", "1")),
        ("copy", "represent", Cardinality("1", "1")),
        ("book", "represent", Cardinality("0", "N")),
    ):
        model.create_relation(entity_id, association_id, cardinality)
    return model


def test_library_scenario_finds_path_cardinalities_and_attributes() -> None:
    model = library_model()
    before = copy.deepcopy(model)
    scenario = parse_scenario(
        "Emprunter un livre",
        """Un lecteur peut effectuer plusieurs emprunts
Un exemplaire peut être emprunté plusieurs fois dans le temps
Un emprunt possède une date de début
Un emprunt possède une date de retour
Déterminer si un exemplaire est disponible à une date donnée""",
    )

    report = BusinessScenarioAnalyzer().analyze(model, scenario)

    assert {item.label for item in report.path}.issuperset(
        {"LECTEUR", "EMPRUNT", "EXEMPLAIRE", "LIVRE"}
    )
    assert len(report.satisfied) == 4
    assert not report.risks
    assert len(report.unverifiable) == 1
    assert "absence de chevauchement" in report.unverifiable[0].explanation
    assert model.entities == before.entities
    assert model.relations == before.relations


def test_missing_required_attribute_is_reported_as_a_risk() -> None:
    model = library_model()
    loan = model.entities["loan"]
    loan.attributes = [item for item in loan.attributes if item.name != "date_retour"]
    scenario = parse_scenario(
        "Retourner un livre", "Un emprunt possède une date de retour"
    )

    report = BusinessScenarioAnalyzer().analyze(model, scenario)

    assert report.checks[0].status is ScenarioCheckStatus.RISK
    assert "Aucun attribut" in report.checks[0].explanation


def test_unconnected_concepts_are_reported_as_a_risk() -> None:
    model = library_model()
    model.relations = {
        key: relation
        for key, relation in model.relations.items()
        if relation.entity_id != "book"
    }
    scenario = parse_scenario("Catalogue", "Un lecteur consulte un livre")

    report = BusinessScenarioAnalyzer().analyze(model, scenario)

    assert report.checks[0].status is ScenarioCheckStatus.RISK
    assert "aucun chemin" in report.checks[0].explanation.casefold()


def test_business_scenario_dialog_displays_report_and_copies_it(qapp) -> None:  # type: ignore[no-untyped-def]
    dialog = BusinessScenarioDialog(library_model())
    dialog.title_edit.setText("Emprunter un livre")
    dialog.expectations_edit.setPlainText(
        "Un lecteur peut effectuer plusieurs emprunts\n"
        "Un emprunt possède une date de début"
    )

    dialog.analyze()
    dialog.copy_report()

    assert dialog.current_report is not None
    assert dialog.checks_tree.topLevelItemCount() == 2
    assert "LECTEUR" in dialog.path_view.toPlainText()
    assert "SCÉNARIO — Emprunter un livre" in qapp.clipboard().text()
    dialog.close()


def test_main_window_exposes_business_scenarios(qapp) -> None:  # type: ignore[no-untyped-def]
    window = MainWindow()

    assert window.business_scenario_action.text() == "Tester un scénario métier…"
    assert window.business_scenario_action.shortcut().toString()

    window.controller.undo_stack.setClean()
    window.close()
