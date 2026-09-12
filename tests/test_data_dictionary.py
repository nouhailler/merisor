from __future__ import annotations

from PySide6.QtWidgets import QInputDialog

from merisor.application import (
    DataDictionaryService,
    ModelDocumentationGenerator,
    ModelVersionComparator,
)
from merisor.domain import (
    Attribute,
    BusinessTerm,
    Entity,
    MCDModel,
    MLDDataType,
    MLDDataTypeName,
)
from merisor.persistence import JsonDiagramRepository
from merisor.ui.data_dictionary_dialog import DataDictionaryDialog
from merisor.ui.main_window import MainWindow


def dictionary_model() -> MCDModel:
    model = MCDModel()
    model.add_entity(
        Entity(
            "CLIENT",
            id="client",
            description="Personne ou organisation possédant un compte.",
            attributes=[
                Attribute(
                    "id_client",
                    True,
                    id="client-id",
                    data_type=MLDDataType(MLDDataTypeName.INTEGER),
                    nullable=False,
                    comment="Identifiant stable du client.",
                ),
                Attribute(
                    "email",
                    id="client-email",
                    data_type=MLDDataType(MLDDataTypeName.VARCHAR, length=255),
                    nullable=False,
                    unique=True,
                    comment="Adresse électronique de contact.",
                ),
            ],
        )
    )
    model.add_business_term(
        BusinessTerm(
            "Client",
            "Personne ou organisation utilisant le service.",
            ("acheteur", "utilisateur"),
            id="term-client",
        )
    )
    return model


def test_dictionary_exposes_semantics_and_attribute_properties() -> None:
    dictionary = DataDictionaryService().build(dictionary_model())

    entity = next(item for item in dictionary.entries if item.id == "client")
    email = next(item for item in dictionary.entries if item.id == "client-email")
    term = next(item for item in dictionary.entries if item.id == "term-client")
    assert "organisation" in entity.description
    assert email.type_label == "VARCHAR(255)"
    assert email.role == "donnée métier"
    assert email.nullable == "non"
    assert email.unique
    assert term.synonyms == ("acheteur", "utilisateur")
    assert "Synonymes" in term.render()


def test_dictionary_round_trip_and_old_json_defaults() -> None:
    repository = JsonDiagramRepository()
    data = repository.to_dict(dictionary_model())

    restored = repository.from_dict(data)
    assert restored.entities["client"].description.startswith("Personne")
    assert restored.business_terms["term-client"].synonyms == (
        "acheteur",
        "utilisateur",
    )

    data.pop("business_terms")
    for entity in data["entities"]:
        entity.pop("description")
    legacy_shape = repository.from_dict(data)
    assert legacy_shape.entities["client"].description == ""
    assert legacy_shape.business_terms == {}


def test_generated_documentation_includes_descriptions_and_glossary() -> None:
    documentation = ModelDocumentationGenerator().generate(dictionary_model())

    assert "Personne ou organisation possédant un compte" in documentation.markdown
    assert "### Glossaire métier" in documentation.markdown
    assert "acheteur, utilisateur" in documentation.markdown
    assert "Glossaire métier" in documentation.html


def test_version_comparison_includes_dictionary_changes() -> None:
    reference = dictionary_model()
    current = dictionary_model()
    current.entities["client"].description = "Définition révisée."
    current.business_terms["term-client"].synonyms += ("adhérent",)

    comparison = ModelVersionComparator().compare(reference, current)

    assert any(change.category == "description" for change in comparison.changes)
    assert any(change.category == "synonymes" for change in comparison.changes)


def test_dictionary_dialog_edits_a_copy_and_adds_a_term(
    qapp: object, monkeypatch
) -> None:  # type: ignore[no-untyped-def]
    source = dictionary_model()
    dialog = DataDictionaryDialog(source)
    dialog.description_edit.setPlainText("Nouvelle définition du client.")
    assert dialog._save_current()
    assert source.entities["client"].description.startswith("Personne")
    assert dialog.working_model.entities["client"].description == (
        "Nouvelle définition du client."
    )

    monkeypatch.setattr(
        QInputDialog,
        "getText",
        staticmethod(lambda *_args, **_kwargs: ("Compte", True)),
    )
    dialog._add_term()
    assert any(
        term.name == "Compte" for term in dialog.working_model.business_terms.values()
    )
    dialog.close()


def test_dictionary_application_is_undoable(qapp: object) -> None:
    window = MainWindow()
    window.controller.load_transient_model(dictionary_model())
    candidate = dictionary_model()
    candidate.entities["client"].description = "Description modifiée."

    window.controller.apply_data_dictionary_model(candidate)
    assert window.controller.model.entities["client"].description == (
        "Description modifiée."
    )
    assert (
        window.controller.undo_stack.undoText() == "Modifier le dictionnaire de données"
    )
    window.controller.undo_stack.undo()
    assert window.controller.model.entities["client"].description.startswith("Personne")
    window.controller.undo_stack.setClean()
    window.close()


def test_main_window_exposes_data_dictionary(qapp: object) -> None:
    window = MainWindow()

    assert window.data_dictionary_action.text() == "Dictionnaire de données…"
    assert window.data_dictionary_action.shortcut().toString() == "Ctrl+Alt+G"

    window.controller.undo_stack.setClean()
    window.close()
