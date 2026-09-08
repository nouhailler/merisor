from __future__ import annotations

from copy import deepcopy

from merisor.domain import (
    Association,
    Attribute,
    Entity,
    MCDModel,
    MLDDataType,
    MLDDataTypeName,
    QualityCategory,
    QualityDimension,
    QualityFindingKind,
    analyze_model_quality,
)
from merisor.persistence import JsonDiagramRepository
from merisor.ui.main_window import MainWindow
from merisor.ui.quality_dialog import QualityReportDialog


def add_entity(
    model: MCDModel,
    name: str,
    *attribute_names: str,
) -> Entity:
    entity = Entity(
        name,
        attributes=[
            Attribute(f"id_{name.casefold()}", identifier=True),
            *(Attribute(attribute_name) for attribute_name in attribute_names),
        ],
    )
    model.add_entity(entity)
    return entity


def findings_for(model: MCDModel, category: QualityCategory) -> tuple[str, ...]:
    return tuple(
        finding.message
        for finding in analyze_model_quality(model).findings
        if finding.category is category
    )


def test_attribute_names_suggest_explainable_logical_types() -> None:
    model = MCDModel()
    product = add_entity(
        model,
        "PRODUIT",
        "date_creation",
        "prix",
        "description",
        "est_actif",
    )
    product.attributes[-1].data_type = MLDDataType(MLDDataTypeName.BOOLEAN)

    report = analyze_model_quality(model)
    type_findings = [
        finding
        for finding in report.findings
        if finding.category is QualityCategory.TYPE_SUGGESTION
    ]

    assert {finding.suggested_value for finding in type_findings} == {
        "DATE",
        "DECIMAL(10,2)",
        "TEXT",
    }
    assert all(finding.rationale for finding in type_findings)
    assert not any("est_actif" in finding.message for finding in type_findings)


def test_email_and_login_receive_uniqueness_suggestions() -> None:
    model = MCDModel()
    add_entity(model, "CLIENT", "email", "login", "nom")

    messages = findings_for(model, QualityCategory.UNIQUENESS)

    assert any("CLIENT.email" in message for message in messages)
    assert any("CLIENT.login" in message for message in messages)
    assert not any("CLIENT.nom" in message for message in messages)


def test_similar_entities_use_names_and_shared_attributes() -> None:
    model = MCDModel()
    add_entity(model, "CLIENT", "nom", "email", "telephone")
    add_entity(model, "ACHETEUR", "nom", "email", "telephone")

    messages = findings_for(model, QualityCategory.SIMILAR_ENTITY)

    assert len(messages) == 1
    assert "CLIENT" in messages[0]
    assert "ACHETEUR" in messages[0]


def test_inheritance_parent_and_child_are_not_reported_as_duplicates() -> None:
    model = MCDModel()
    person = add_entity(model, "PERSONNE", "nom", "email", "telephone")
    customer = add_entity(model, "CLIENT", "nom", "email", "telephone")
    model.create_inheritance(person.id, (customer.id,))

    assert not findings_for(model, QualityCategory.SIMILAR_ENTITY)


def test_inconsistent_naming_is_compared_with_the_dominant_convention() -> None:
    model = MCDModel()
    add_entity(model, "CLIENT", "nom")
    add_entity(model, "COMMANDE", "numero")
    add_entity(model, "PRODUIT", "libelle")
    add_entity(model, "AdresseLivraison", "rue")

    messages = findings_for(model, QualityCategory.NAMING)

    assert any("AdresseLivraison" in message for message in messages)
    assert any("MAJUSCULES_AVEC_UNDERSCORE" in message for message in messages)


def test_normalization_smells_cover_repetition_lists_and_foreign_ids() -> None:
    model = MCDModel()
    add_entity(model, "CLIENT", "nom")
    add_entity(
        model,
        "COMMANDE",
        "telephone1",
        "telephone2",
        "tags",
        "id_client",
    )

    report = analyze_model_quality(model)
    codes = {
        finding.code
        for finding in report.findings
        if finding.category is QualityCategory.NORMALIZATION
    }

    assert "quality.normalization.repeating_group" in codes
    assert "quality.normalization.multivalued_attribute" in codes
    assert "quality.normalization.foreign_id_in_mcd" in codes


def test_score_is_weighted_deterministic_and_explains_every_deduction() -> None:
    model = MCDModel()
    add_entity(model, "PILOTE", "nom")

    clean = analyze_model_quality(model)
    repeated = analyze_model_quality(model)

    assert clean == repeated
    assert clean.overall_score == 100
    assert sum(dimension.weight for dimension in clean.dimensions) == 100
    assert all(dimension.score == 100 for dimension in clean.dimensions)

    next(iter(model.entities.values())).attributes.append(Attribute("date_naissance"))
    degraded = analyze_model_quality(model)
    typing = degraded.dimension(QualityDimension.TYPING)

    assert degraded.overall_score < clean.overall_score
    assert typing.score == 92
    assert typing.deductions


def test_quality_analysis_never_mutates_the_mcd() -> None:
    model = MCDModel()
    add_entity(model, "CLIENT", "email", "date_naissance")
    repository = JsonDiagramRepository()
    before = deepcopy(repository.to_dict(model))

    analyze_model_quality(model)

    assert repository.to_dict(model) == before


def test_quality_action_and_report_are_available_in_the_main_window(qapp) -> None:  # type: ignore[no-untyped-def]
    window = MainWindow()
    add_entity(window.controller.model, "PILOTE", "nom")
    report = window.controller.analyze_quality()
    dialog = QualityReportDialog(report)

    assert window.quality_action.text() == "Analyser la qualité du modèle…"
    assert window.quality_action.shortcut().toString() == "Ctrl+Shift+Q"
    assert dialog.overall_progress.value() == report.overall_score
    assert dialog.score_tree.topLevelItemCount() == 6
    assert dialog.findings_tree.topLevelItemCount() == 3
    assert "pas une certification" in dialog.disclaimer_label.text()

    dialog.close()
    window.controller.undo_stack.setClean()
    window.close()
    qapp.processEvents()


def test_report_separates_errors_risks_and_suggestions() -> None:
    model = MCDModel()
    entity = Entity("CLIENT", attributes=[Attribute("email"), Attribute("valeur")])
    model.add_entity(entity)

    report = analyze_model_quality(model)

    assert any(item.code == "entity.identifier_missing" for item in report.errors)
    assert any(
        item.code == "quality.naming.ambiguous_attribute" for item in report.risks
    )
    assert any(
        item.code == "quality.attribute.uniqueness_suggestion"
        for item in report.suggestions
    )
    assert all(item.kind is QualityFindingKind.ERROR for item in report.errors)
    assert all(item.kind is QualityFindingKind.RISK for item in report.risks)
    assert all(
        item.kind is QualityFindingKind.SUGGESTION for item in report.suggestions
    )


def test_score_is_explicitly_heuristic_and_deductions_are_quantified() -> None:
    model = MCDModel()
    add_entity(model, "CLIENT", "date_naissance")

    report = analyze_model_quality(model)

    assert report.score_is_heuristic
    assert "ne certifie" in report.score_explanation
    assert any(
        deduction.startswith("-") and "points" in deduction
        for dimension in report.dimensions
        for deduction in dimension.deductions
    )


def test_generic_association_name_is_a_risk_not_an_error() -> None:
    model = MCDModel()
    add_entity(model, "CLIENT", "nom")
    model.add_association(Association("GERER"))

    report = analyze_model_quality(model)
    generic = next(
        item
        for item in report.risks
        if item.code == "quality.naming.generic_association"
    )

    assert generic.kind is QualityFindingKind.RISK
    assert generic not in report.errors
