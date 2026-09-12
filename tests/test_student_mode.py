from __future__ import annotations

import copy

from merisor.application import (
    COMMAND_ORDER_EXERCISE,
    StudentCriterionStatus,
    StudentExerciseEvaluator,
)
from merisor.domain import Association, Attribute, Cardinality, Entity, MCDModel
from merisor.ui.main_window import MainWindow
from merisor.ui.student_mode_dialog import StudentModeDialog


def exercise_model(*, wrong_client_cardinality: bool = False) -> MCDModel:
    model = MCDModel()
    client = Entity("CLIENT", id="client", attributes=[Attribute("id_client", True)])
    order = Entity("COMMANDE", id="order", attributes=[Attribute("id_commande", True)])
    product = Entity(
        "PRODUIT", id="product", attributes=[Attribute("id_produit", True)]
    )
    place = Association("PASSER", id="place")
    contain = Association("CONTENIR", id="contain")
    for entity in (client, order, product):
        model.add_entity(entity)
    model.add_association(place)
    model.add_association(contain)
    model.create_relation(
        client.id,
        place.id,
        Cardinality("1", "1") if wrong_client_cardinality else Cardinality("0", "N"),
    )
    model.create_relation(order.id, place.id, Cardinality("1", "1"))
    model.create_relation(order.id, contain.id, Cardinality("1", "N"))
    model.create_relation(product.id, contain.id, Cardinality("0", "N"))
    return model


def test_complete_exercise_receives_full_explicable_score_without_mutation() -> None:
    model = exercise_model()
    before = copy.deepcopy(model)

    report = StudentExerciseEvaluator().evaluate(model, COMMAND_ORDER_EXERCISE)

    assert report.score == 100
    assert report.passed_count == len(report.criteria) == 12
    assert all(
        criterion.status is StudentCriterionStatus.PASSED
        for criterion in report.criteria
    )
    assert "Pourquoi ?" in report.render()
    assert "pas une vérité métier universelle" in report.render()
    assert model.entities == before.entities
    assert model.associations == before.associations
    assert model.relations == before.relations


def test_wrong_cardinality_is_explained_as_a_learning_point() -> None:
    report = StudentExerciseEvaluator().evaluate(
        exercise_model(wrong_client_cardinality=True), COMMAND_ORDER_EXERCISE
    )

    criterion = next(
        item for item in report.criteria if item.label == "Cardinalité CLIENT (0,N)"
    )
    assert criterion.status is StudentCriterionStatus.NEEDS_WORK
    assert "(1,1)" in criterion.explanation
    assert "aucune commande" in criterion.why
    assert report.score < 100


def test_missing_concepts_and_identifiers_are_reported() -> None:
    model = MCDModel()
    model.add_entity(Entity("CLIENT", attributes=[Attribute("nom")]))

    report = StudentExerciseEvaluator().evaluate(model, COMMAND_ORDER_EXERCISE)

    assert any(
        item.label == "Identifiant de CLIENT"
        and item.status is StudentCriterionStatus.NEEDS_WORK
        for item in report.criteria
    )
    assert any(
        item.label == "Entité COMMANDE"
        and item.status is StudentCriterionStatus.NEEDS_WORK
        for item in report.criteria
    )


def test_student_dialog_displays_score_and_why(qapp: object) -> None:
    dialog = StudentModeDialog(exercise_model())

    assert "Un client peut passer" in dialog.statement.toPlainText()
    assert "Hypothèses explicites" in dialog.assumptions.text()
    dialog.evaluate()
    assert dialog.score.value() == 100
    assert dialog.criteria.topLevelItemCount() == 12
    first = dialog.criteria.topLevelItem(0)
    assert first is not None
    dialog.criteria.setCurrentItem(first)
    assert "Pourquoi ?" in dialog.details.toPlainText()
    assert dialog.copy_button.isEnabled()
    dialog.close()


def test_main_window_exposes_student_mode(qapp: object) -> None:
    window = MainWindow()

    assert window.student_mode_action.text() == "🎓 Mode étudiant…"
    assert window.student_mode_action.shortcut().toString() == "Ctrl+Alt+U"

    window.controller.undo_stack.setClean()
    window.close()
