from __future__ import annotations

import copy

import pytest
from PySide6.QtCore import QPointF, Qt

from merisor.application import DiagramController, SubmodelResolver
from merisor.domain import (
    Association,
    Attribute,
    DiagramError,
    Entity,
    MCDModel,
    ModelDomain,
    SubmodelView,
    SubmodelViewKind,
)
from merisor.persistence import JsonDiagramRepository, PersistenceError
from merisor.ui.canvas import DiagramScene
from merisor.ui.main_window import MainWindow
from merisor.ui.model_explorer_dialog import ModelExplorerDialog
from merisor.ui.submodel_dialog import SubmodelManagerDialog


def scoped_model() -> MCDModel:
    model = MCDModel()
    client = Entity(
        "CLIENT",
        id="entity.client",
        attributes=[Attribute("id_client", True, id="attribute.client.id")],
    )
    product = Entity(
        "PRODUIT",
        id="entity.product",
        attributes=[Attribute("id_produit", True, id="attribute.product.id")],
    )
    payment = Entity(
        "PAIEMENT",
        id="entity.payment",
        attributes=[Attribute("id_paiement", True, id="attribute.payment.id")],
    )
    purchase = Association("ACHETER", id="association.purchase")
    for entity in (client, product, payment):
        model.add_entity(entity)
    model.add_association(purchase)
    users = ModelDomain(
        "Utilisateurs",
        (client.id,),
        id="domain.users",
        description="Identité et comptes",
    )
    commerce = ModelDomain(
        "Commerce",
        (product.id, purchase.id),
        id="domain.commerce",
    )
    model.add_domain(users)
    model.add_domain(commerce)
    model.add_submodel_view(
        SubmodelView(
            "Parcours client",
            SubmodelViewKind.BUSINESS,
            (users.id, commerce.id),
            id="view.customer",
        )
    )
    model.add_submodel_view(
        SubmodelView(
            "Exploitation",
            SubmodelViewKind.TECHNICAL,
            node_ids=(payment.id,),
            id="view.operations",
        )
    )
    return model


def test_domains_and_views_are_first_class_validated_objects() -> None:
    model = scoped_model()
    assert model.domains["domain.users"].node_ids == ("entity.client",)
    assert model.submodel_views["view.customer"].kind is SubmodelViewKind.BUSINESS

    with pytest.raises(DiagramError, match="objet inconnu"):
        model.add_domain(ModelDomain("Invalide", ("absent",)))
    with pytest.raises(DiagramError, match="Domaine déjà présent"):
        model.add_domain(ModelDomain("utilisateurs"))
    with pytest.raises(DiagramError, match="domaine inconnu"):
        model.add_submodel_view(SubmodelView("Vue invalide", "BUSINESS", ("absent",)))


def test_resolver_exposes_global_domain_business_and_technical_views() -> None:
    model = scoped_model()
    scopes = SubmodelResolver().scopes(model)
    assert [(scope.category, scope.label) for scope in scopes] == [
        ("GLOBAL", "Vue globale"),
        ("DOMAIN", "Commerce"),
        ("DOMAIN", "Utilisateurs"),
        ("BUSINESS", "Parcours client"),
        ("TECHNICAL", "Exploitation"),
    ]
    business = SubmodelResolver().resolve(model, "view:view.customer")
    assert business.node_ids == frozenset(
        {"entity.client", "entity.product", "association.purchase"}
    )
    technical = SubmodelResolver().resolve(model, "view:view.operations")
    assert technical.node_ids == frozenset({"entity.payment"})


def test_json_round_trip_preserves_submodels_and_old_v2_defaults() -> None:
    repository = JsonDiagramRepository()
    model = scoped_model()
    data = repository.to_dict(model)
    restored = repository.from_dict(data)

    assert data["domains"][0]["node_ids"]
    assert data["submodel_views"][0]["kind"] in {"BUSINESS", "TECHNICAL"}
    assert restored.domains == model.domains
    assert restored.submodel_views == model.submodel_views

    legacy_v2 = {
        "format_version": 2,
        "entities": [],
        "associations": [],
        "relations": [],
    }
    old_model = repository.from_dict(legacy_v2)
    assert old_model.domains == {}
    assert old_model.submodel_views == {}


def test_json_rejects_orphan_submodel_references() -> None:
    data = JsonDiagramRepository().to_dict(MCDModel())
    data["domains"] = [
        {
            "id": "domain.invalid",
            "name": "Invalide",
            "description": "",
            "node_ids": ["absent"],
        }
    ]
    with pytest.raises(PersistenceError, match="objet inconnu"):
        JsonDiagramRepository().from_dict(data)


def test_node_deletion_prunes_membership_and_undo_restores_it(qapp) -> None:  # type: ignore[no-untyped-def]
    controller = DiagramController(DiagramScene())
    client = controller.create_entity("CLIENT", QPointF())
    controller.apply_submodel_configuration(
        (ModelDomain("Utilisateurs", (client.id,), id="domain.users"),), ()
    )
    controller._node_items[client.id].setSelected(True)
    controller.delete_selected()

    assert client.id not in controller.model.entities
    assert controller.model.domains["domain.users"].node_ids == ()
    controller.undo_stack.undo()
    assert client.id in controller.model.entities
    assert list(controller.model.domains["domain.users"].node_ids) == [client.id]


def test_controller_applies_whole_configuration_as_one_undoable_change(qapp) -> None:  # type: ignore[no-untyped-def]
    controller = DiagramController(DiagramScene())
    entity = controller.create_entity("CLIENT", QPointF())
    controller.add_attribute(entity.id, "id_client", True)
    generated_mld = controller.generate_mld()
    controller.undo_stack.setClean()
    controller.apply_submodel_configuration(
        (ModelDomain("Utilisateurs", (entity.id,), id="domain.users"),), ()
    )
    assert set(controller.model.domains) == {"domain.users"}
    assert controller.is_dirty
    assert controller.mld_model is generated_mld
    assert not controller.mld_is_stale
    controller.undo_stack.undo()
    assert controller.model.domains == {}
    controller.undo_stack.redo()
    assert set(controller.model.domains) == {"domain.users"}


def test_manager_edits_a_copy_until_explicit_application(qapp) -> None:  # type: ignore[no-untyped-def]
    model = MCDModel()
    entity = Entity(
        "CLIENT",
        id="entity.client",
        attributes=[Attribute("id_client", True, id="attribute.client.id")],
    )
    model.add_entity(entity)
    before = copy.deepcopy(model)
    dialog = SubmodelManagerDialog(model)
    dialog._add_domain()
    dialog.domain_name.setText("Utilisateurs")
    entity_group = dialog.domain_nodes.topLevelItem(0)
    assert entity_group is not None
    entity_item = entity_group.child(0)
    assert entity_item is not None
    entity_item.setCheckState(0, Qt.CheckState.Checked)
    assert dialog._save_domain()

    assert model.domains == before.domains
    saved_domain = next(iter(dialog.domains.values()))
    assert saved_domain.name == "Utilisateurs"
    assert saved_domain.node_ids == (entity.id,)
    dialog.close()


def test_explorer_can_switch_between_saved_scopes(qapp) -> None:  # type: ignore[no-untyped-def]
    model = scoped_model()
    dialog = ModelExplorerDialog(model)
    domain_index = dialog.scope_combo.findData("domain:domain.users")
    dialog.scope_combo.setCurrentIndex(domain_index)
    qapp.processEvents()
    assert set(dialog.controller.model.entities) == {"entity.client"}

    view_index = dialog.scope_combo.findData("view:view.customer")
    dialog.scope_combo.setCurrentIndex(view_index)
    qapp.processEvents()
    assert set(dialog.controller.model.entities) == {
        "entity.client",
        "entity.product",
    }
    assert set(dialog.controller.model.associations) == {"association.purchase"}
    dialog.close()


def test_main_window_exposes_submodel_management(qapp) -> None:  # type: ignore[no-untyped-def]
    window = MainWindow()
    assert window.manage_submodels_action.text() == "Gérer les domaines et vues…"
    assert window.manage_submodels_action.shortcut().toString()
    window.close()
