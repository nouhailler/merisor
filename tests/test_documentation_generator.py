from __future__ import annotations

from merisor.application import ModelDocumentationGenerator
from merisor.domain import (
    Association,
    Attribute,
    Cardinality,
    Entity,
    MCDModel,
    MLDDataType,
    MLDDataTypeName,
)


def _commerce_model() -> MCDModel:
    model = MCDModel()
    client = Entity(
        "CLIENT",
        id="client",
        attributes=[
            Attribute(
                "id_client",
                True,
                id="client-id",
                data_type=MLDDataType(MLDDataTypeName.INTEGER),
                nullable=False,
                auto_increment=True,
            ),
            Attribute(
                "email",
                id="client-email",
                data_type=MLDDataType.varchar(255),
                unique=True,
                comment="Adresse de contact",
                constraints=("length(email) > 3",),
            ),
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


def test_documentation_covers_mcd_mld_constraints_and_technical_view() -> None:
    documentation = ModelDocumentationGenerator().generate(
        _commerce_model(), project_name="Commerce"
    )

    assert documentation.includes_mld
    assert not documentation.warnings
    assert "# Documentation — Commerce" in documentation.markdown
    assert "## Modèle conceptuel" in documentation.markdown
    assert "```mermaid" in documentation.markdown
    assert "#### CLIENT" in documentation.markdown
    assert "`0,N`" in documentation.markdown
    assert "## Modèle logique" in documentation.markdown
    assert "PK" in documentation.markdown
    assert "FK" in documentation.markdown
    assert "CHECK (length(email) > 3)" in documentation.markdown
    assert "## Documentation technique" in documentation.markdown
    assert "cardinalite: 0,N" in documentation.markdown
    assert "<h2>Modèle conceptuel</h2>" in documentation.html
    assert "Adresse de contact" in documentation.html
    assert "Documentation technique" in documentation.html


def test_invalid_mcd_is_documented_without_modifying_or_inventing_an_mld() -> None:
    model = MCDModel()
    model.add_entity(Entity("CLIENT", id="client"))

    documentation = ModelDocumentationGenerator().generate(model)

    assert not documentation.includes_mld
    assert documentation.warnings
    assert "MLD indisponible" in documentation.markdown
    assert "Description : *non renseignée dans le MCD.*" in documentation.markdown
    assert model.entities["client"].attributes == []


def test_documentation_generation_is_deterministic() -> None:
    generator = ModelDocumentationGenerator()
    model = _commerce_model()

    first = generator.generate(model, project_name="Commerce")
    second = generator.generate(model, project_name="Commerce")

    assert first.markdown == second.markdown
    assert first.html == second.html


def test_html_escapes_user_content_and_embeds_provided_diagrams() -> None:
    model = MCDModel()
    model.add_entity(
        Entity(
            "CLIENT <VIP>",
            id="client",
            attributes=[Attribute("id&client", True, id="client-id")],
        )
    )

    documentation = ModelDocumentationGenerator().generate(
        model,
        mcd_image_data_uri="data:image/png;base64,AAAA",
    )

    assert "CLIENT &lt;VIP&gt;" in documentation.html
    assert "id&amp;client" in documentation.html
    assert 'src="data:image/png;base64,AAAA"' in documentation.html
