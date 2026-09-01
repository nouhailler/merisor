from __future__ import annotations

from pathlib import Path

from merisor.application import DiagramTextExporter, McdToMldTransformer
from merisor.domain import Association, Attribute, Cardinality, Entity, MCDModel


def _sample_mcd() -> MCDModel:
    model = MCDModel()
    client = Entity(
        "CLIENT",
        id="client",
        attributes=[
            Attribute("id_client", True, id="client-id"),
            Attribute("nom", id="client-name"),
        ],
    )
    order = Entity(
        "COMMANDE",
        id="order",
        attributes=[Attribute("id_commande", True, id="order-id")],
    )
    association = Association("PASSER", id="place")
    model.add_entity(client)
    model.add_entity(order)
    model.add_association(association)
    model.create_relation(client.id, association.id, Cardinality("0", "N"))
    model.create_relation(order.id, association.id, Cardinality("1", "1"))
    return model


def test_mermaid_mcd_export_preserves_nodes_attributes_and_cardinalities(
    tmp_path: Path,
) -> None:
    output = tmp_path / "commerce.mmd"

    DiagramTextExporter().export_mcd(_sample_mcd(), output)
    text = output.read_text(encoding="utf-8")

    assert text.startswith("flowchart LR\n")
    assert "CLIENT&lt;" not in text
    assert "CLIENT<br/># id_client : INTEGER<br/>nom : VARCHAR(100)" in text
    assert '{"PASSER"}' in text
    assert '|"0,N"|' in text
    assert '|"1,1"|' in text


def test_graphviz_mcd_export_is_deterministic_and_includes_relations() -> None:
    exporter = DiagramTextExporter()
    model = _sample_mcd()

    first = exporter.render_mcd_graphviz(model)
    second = exporter.render_mcd_graphviz(model)

    assert first == second
    assert first.startswith("digraph MERISOR_MCD")
    assert "shape=diamond" in first
    assert 'label="0,N"' in first


def test_mermaid_and_graphviz_mld_exports_include_foreign_keys(
    tmp_path: Path,
) -> None:
    mld = McdToMldTransformer().transform(_sample_mcd())
    mermaid_path = tmp_path / "commerce.mermaid"
    dot_path = tmp_path / "commerce.dot"
    exporter = DiagramTextExporter()

    exporter.export_mld(mld, mermaid_path)
    exporter.export_mld(mld, dot_path)
    mermaid = mermaid_path.read_text(encoding="utf-8")
    dot = dot_path.read_text(encoding="utf-8")

    assert "PK id_client : INTEGER" in mermaid
    assert "FK id_client : INTEGER" in mermaid
    assert '-->|"FK id_client"|' in mermaid
    assert dot.startswith("digraph MERISOR_MLD")
    assert 'label="FK id_client"' in dot
