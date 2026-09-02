from __future__ import annotations

from merisor.application import McdToMldTransformer, MldTransformationExplainer
from merisor.domain import (
    Association,
    Attribute,
    Cardinality,
    Entity,
    Inheritance,
    MCDModel,
    MLDTable,
    Relation,
)


def _entity(name: str, identifier_name: str, entity_id: str) -> Entity:
    return Entity(
        name,
        id=entity_id,
        attributes=[Attribute(identifier_name, True, id=f"attribute:{entity_id}")],
    )


def _one_to_many() -> tuple[MCDModel, MLDTable]:
    model = MCDModel()
    client = _entity("CLIENT", "id_client", "client")
    order = _entity("COMMANDE", "id_commande", "order")
    association = Association("PASSER", id="passer")
    model.add_entity(client)
    model.add_entity(order)
    model.add_association(association)
    model.add_relation(
        Relation(
            client.id,
            association.id,
            id="client-passer",
            cardinality=Cardinality("0", "N"),
        )
    )
    model.add_relation(
        Relation(
            order.id,
            association.id,
            id="order-passer",
            cardinality=Cardinality("1", "1"),
        )
    )
    mld = McdToMldTransformer().transform(model)
    return model, mld.table("COMMANDE")


def test_explains_entity_fk_nullability_and_source_cardinality() -> None:
    model, order_table = _one_to_many()
    mld = McdToMldTransformer().transform(model)

    report = MldTransformationExplainer().explain_table(model, mld, order_table)
    rendered = report.render_text()

    assert report.table_name == "COMMANDE"
    assert "L'entité COMMANDE est devenue la table COMMANDE" in rendered
    assert "FK vers CLIENT" in rendered
    assert "Association PASSER, cardinalité (0,N)" in rendered
    assert "id_client de CLIENT a migré dans COMMANDE" in rendered
    assert "NULL (facultative)" in rendered
    assert "aucune IA" in report.headline


def test_explains_historized_table_and_technical_primary_key() -> None:
    model = MCDModel()
    pilot = _entity("PILOTE", "id_pilote", "pilot")
    team = _entity("EQUIPE", "id_equipe", "team")
    engagement = Association(
        "ENGAGER",
        id="engage",
        is_historized=True,
        attributes=[Attribute("date_debut", id="start-date")],
    )
    model.add_entity(pilot)
    model.add_entity(team)
    model.add_association(engagement)
    model.add_relation(
        Relation(
            pilot.id,
            engagement.id,
            id="pilot-link",
            cardinality=Cardinality("0", "N"),
        )
    )
    model.add_relation(
        Relation(
            team.id,
            engagement.id,
            id="team-link",
            cardinality=Cardinality("1", "1"),
        )
    )
    mld = McdToMldTransformer().transform(model)

    report = MldTransformationExplainer().explain_table(
        model, mld, mld.table("ENGAGER")
    )
    rendered = report.render_text()

    assert "association historisée" in rendered
    assert "clé technique déterministe et auto-incrémentée" in rendered
    assert "Colonne date_debut" in rendered
    assert "FK vers PILOTE" in rendered
    assert "FK vers EQUIPE" in rendered


def test_explains_many_to_many_composite_key_without_calling_it_technical() -> None:
    model = MCDModel()
    author = _entity("AUTEUR", "id_auteur", "author")
    book = _entity("LIVRE", "id_livre", "book")
    writing = Association("ECRIRE", id="writing")
    model.add_entity(author)
    model.add_entity(book)
    model.add_association(writing)
    model.add_relation(
        Relation(
            author.id,
            writing.id,
            id="author-link",
            cardinality=Cardinality("0", "N"),
        )
    )
    model.add_relation(
        Relation(
            book.id,
            writing.id,
            id="book-link",
            cardinality=Cardinality("1", "N"),
        )
    )
    mld = McdToMldTransformer().transform(model)

    rendered = (
        MldTransformationExplainer()
        .explain_table(model, mld, mld.table("ECRIRE"))
        .render_text()
    )

    assert "Une association N:N devient une table d'association" in rendered
    assert "les FK issues des participants composent la PK" in rendered
    assert "clé technique déterministe" not in rendered


def test_explains_unique_constraint_created_by_one_to_one() -> None:
    model = MCDModel()
    person = _entity("PERSONNE", "id_personne", "person")
    passport = _entity("PASSEPORT", "id_passeport", "passport")
    ownership = Association("POSSEDER", id="ownership")
    model.add_entity(person)
    model.add_entity(passport)
    model.add_association(ownership)
    model.add_relation(
        Relation(
            person.id,
            ownership.id,
            id="person-link",
            cardinality=Cardinality("1", "1"),
        )
    )
    model.add_relation(
        Relation(
            passport.id,
            ownership.id,
            id="passport-link",
            cardinality=Cardinality("0", "1"),
        )
    )
    mld = McdToMldTransformer().transform(model)
    person_table = mld.table("PERSONNE")

    rendered = (
        MldTransformationExplainer()
        .explain_table(model, mld, person_table)
        .render_text()
    )

    assert "Contrainte UNIQUE" in rendered
    assert "Dans une association 1:1" in rendered


def test_explains_joined_inheritance_primary_key_and_foreign_key() -> None:
    model = MCDModel()
    person = _entity("PERSONNE", "id_personne", "person")
    customer = _entity("CLIENT", "id_client", "customer")
    model.add_entity(person)
    model.add_entity(customer)
    model.add_inheritance(
        Inheritance(person.id, (customer.id,), "JOINED", id="person-customer")
    )
    mld = McdToMldTransformer().transform(model)

    rendered = (
        MldTransformationExplainer()
        .explain_table(model, mld, mld.table("CLIENT"))
        .render_text()
    )

    assert "Avec la stratégie ISA JOINED" in rendered
    assert "FK vers PERSONNE" in rendered
    assert "La PK de la table fille est également une FK" in rendered
