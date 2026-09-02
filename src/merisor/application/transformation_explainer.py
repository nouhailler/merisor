"""Explications pédagogiques déterministes de la transformation MCD → MLD."""

from __future__ import annotations

from dataclasses import dataclass

from merisor.domain import (
    Association,
    Attribute,
    CardinalityMaximum,
    Entity,
    MaterializationStrategy,
    MCDModel,
    MLDColumn,
    MLDForeignKey,
    MLDModel,
    MLDTable,
    MLDTableSource,
    Relation,
)


@dataclass(frozen=True, slots=True)
class TransformationExplanation:
    """Une décision MCD → MLD et sa justification vérifiable."""

    code: str
    title: str
    result: str
    rule: str
    source: str

    @property
    def text(self) -> str:
        return (
            f"{self.result}\n\nRègle appliquée\n{self.rule}\n\n"
            f"Provenance MCD\n{self.source}"
        )


@dataclass(frozen=True, slots=True)
class TransformationExplanationReport:
    table_name: str
    headline: str
    explanations: tuple[TransformationExplanation, ...]

    def render_text(self) -> str:
        sections = [f"POURQUOI ? — {self.table_name}", self.headline]
        for explanation in self.explanations:
            sections.append(f"{explanation.title}\n{explanation.text}")
        return "\n\n".join(sections)


class MldTransformationExplainer:
    """Explique le résultat à partir des provenances produites par le moteur."""

    def explain_table(
        self,
        mcd: MCDModel,
        mld: MLDModel,
        table: MLDTable,
    ) -> TransformationExplanationReport:
        # Vérifie que l'objet présenté appartient bien au MLD courant.
        mld.table_by_id(table.id)
        explanations = [self._table_explanation(mcd, table)]
        explanations.append(self._primary_key_explanation(mcd, table))
        explanations.extend(
            self._column_explanation(mcd, table, column) for column in table.columns
        )
        explanations.extend(
            self._foreign_key_explanation(mcd, mld, table, foreign_key)
            for foreign_key in table.foreign_keys
        )
        explanations.extend(self._unique_explanations(mcd, table))
        explanations.extend(self._check_explanations(table))
        return TransformationExplanationReport(
            table.name,
            "Ces explications proviennent des identifiants de source conservés "
            "pendant la transformation. Elles ne font appel à aucune IA.",
            tuple(explanations),
        )

    def _table_explanation(
        self, mcd: MCDModel, table: MLDTable
    ) -> TransformationExplanation:
        if table.source is MLDTableSource.ENTITY:
            entity = mcd.entities[table.source_element_id]
            return TransformationExplanation(
                "table.entity",
                f"Table {table.name}",
                f"L'entité {entity.name} est devenue la table {table.name}.",
                "En MERISE, chaque entité conservée dans le MLD produit une table. "
                "Ses attributs deviennent des colonnes et son identifiant devient "
                "la clé primaire.",
                f"Entité {entity.name} ({entity.id})",
            )

        association = mcd.associations[table.source_element_id]
        relations = self._association_relations(mcd, association)
        maxima = [
            relation.cardinality.maximum
            for relation in relations
            if relation.cardinality is not None
        ]
        if len(relations) >= 3:
            rule = (
                f"Une association n-aire ({len(relations)} branches) est "
                "matérialisée en table afin de conserver simultanément toutes "
                "ses références."
            )
        elif maxima and all(item is CardinalityMaximum.MANY for item in maxima):
            rule = (
                "Une association N:N devient une table d'association. Les "
                "identifiants des entités participantes y migrent comme FK."
            )
        elif (
            association.materialization_strategy is MaterializationStrategy.FORCE_TABLE
        ):
            rule = (
                "La stratégie FORCE_TABLE demande explicitement une table "
                "indépendante, même lorsque la règle classique pourrait migrer "
                "une simple FK."
            )
        elif association.is_historized:
            rule = (
                "Une association historisée doit conserver plusieurs occurrences "
                "indépendantes dans le temps ; elle devient donc une table."
            )
        else:
            rule = (
                "Cette association a été matérialisée conformément à sa stratégie "
                "et à ses cardinalités."
            )
        cards = ", ".join(
            f"{mcd.entities[item.entity_id].name} ({item.cardinality.label})"
            for item in relations
            if item.cardinality is not None
        )
        return TransformationExplanation(
            "table.association",
            f"Table d'association {table.name}",
            f"L'association {association.name} est devenue une table indépendante.",
            rule,
            f"Association {association.name} ({association.id}) — {cards}",
        )

    def _primary_key_explanation(
        self, mcd: MCDModel, table: MLDTable
    ) -> TransformationExplanation:
        if not table.primary_key:
            return TransformationExplanation(
                "primary_key.missing",
                "Aucune clé primaire",
                f"La table {table.name} ne possède aucune clé primaire.",
                "Le MCD source ne fournit pas d'identifiant exploitable. Cette "
                "situation est conservée, mais doit être corrigée avant une "
                "génération SQL fiable.",
                f"Élément MCD {table.source_element_id}",
            )
        names = ", ".join(column.name for column in table.primary_key_columns)
        source = mcd.node(table.source_element_id)
        inheritance_key = next(
            (
                foreign_key
                for foreign_key in table.foreign_keys
                if foreign_key.source_inheritance_id is not None
                and foreign_key.column_ids == table.primary_key
            ),
            None,
        )
        if inheritance_key is not None:
            rule = (
                "Avec la stratégie ISA JOINED, la table fille reprend "
                "l'identifiant de la table mère : cette PK est aussi une FK vers "
                "la mère."
            )
        elif table.source is MLDTableSource.ENTITY:
            rule = (
                "Les attributs marqués comme identifiants dans l'entité deviennent "
                "la PK. Plusieurs identifiants produisent une PK composée."
            )
        elif any(
            column.auto_increment and column.id.startswith("column:technical:")
            for column in table.primary_key_columns
        ):
            rule = (
                "L'association matérialisée ne possède pas d'identifiant "
                "conceptuel utilisable ; MERISOR crée une clé technique "
                "déterministe et auto-incrémentée."
            )
        elif isinstance(source, Association) and source.identifier_attributes:
            rule = (
                "L'association possède un identifiant conceptuel explicite ; ses "
                "attributs identifiants deviennent la PK sans clé technique ajoutée."
            )
        else:
            rule = (
                "Sans identifiant propre, les FK issues des participants composent "
                "la PK de cette table d'association."
            )
        return TransformationExplanation(
            "primary_key",
            f"Clé primaire ({names})",
            f"La clé primaire de {table.name} est constituée de {names}.",
            rule,
            f"{source.__class__.__name__} {source.name} ({source.id})",
        )

    def _column_explanation(
        self, mcd: MCDModel, table: MLDTable, column: MLDColumn
    ) -> TransformationExplanation:
        attribute = self._attribute(mcd, column.source_attribute_id)
        owner = self._node(mcd, column.source_element_id)
        nullability = self._nullability(column)
        if column.generated and column.source_relation_id is not None:
            relation = mcd.relations[column.source_relation_id]
            entity = mcd.entities[relation.entity_id]
            card = relation.cardinality.label if relation.cardinality else "inconnue"
            identifier_name = attribute.name if attribute is not None else column.name
            return TransformationExplanation(
                f"column.fk.{column.id}",
                f"Colonne migrée {column.name}",
                f"L'identifiant {identifier_name} de {entity.name} a migré dans "
                f"{table.name} sous le nom {column.name} ({nullability}).",
                "Une FK reprend le type de la colonne référencée. Sa nullabilité "
                "est déterminée par la cardinalité minimale conservée par la "
                "transformation.",
                f"Relation {relation.id}, rôle {relation.role or 'non nommé'}, "
                f"cardinalité ({card})",
            )
        if column.generated:
            return TransformationExplanation(
                f"column.generated.{column.id}",
                f"Colonne technique {column.name}",
                f"MERISOR a généré {column.name} dans {table.name} ({nullability}).",
                "Cette colonne est nécessaire à la matérialisation ou à une "
                "stratégie d'héritage et ne correspond pas à un nouvel attribut "
                "inventé dans le MCD.",
                self._node_label(owner),
            )
        if attribute is None:
            rule = "La colonne est conservée depuis la structure logique source."
            source = self._node_label(owner)
        elif owner is not None and owner.id != table.source_element_id:
            rule = (
                "La stratégie ISA aplatie sélectionnée copie les attributs dans la "
                "table conservée."
            )
            source = f"Attribut {owner.name}.{attribute.name} ({attribute.id})"
        elif isinstance(owner, Association) and table.source is MLDTableSource.ENTITY:
            rule = (
                "Dans une association 1:N non matérialisée, les attributs de "
                "l'association migrent avec la FK dans la table porteuse."
            )
            source = f"Attribut {owner.name}.{attribute.name} ({attribute.id})"
        else:
            type_rule = (
                "son type logique explicite"
                if attribute is not None and attribute.data_type is not None
                else "le type automatique historique de MERISOR"
            )
            rule = f"Un attribut MCD devient une colonne MLD et conserve {type_rule}."
            source = (
                f"Attribut {owner.name}.{attribute.name} ({attribute.id})"
                if owner is not None and attribute is not None
                else self._node_label(owner)
            )
        return TransformationExplanation(
            f"column.attribute.{column.id}",
            f"Colonne {column.name}",
            f"{column.name} est de type {column.data_type.label} et vaut "
            f"{nullability}.",
            rule,
            source,
        )

    def _foreign_key_explanation(
        self,
        mcd: MCDModel,
        mld: MLDModel,
        table: MLDTable,
        foreign_key: MLDForeignKey,
    ) -> TransformationExplanation:
        target = mld.table_by_id(foreign_key.referenced_table_id)
        local_names = ", ".join(
            table.column_by_id(item).name for item in foreign_key.column_ids
        )
        target_names = ", ".join(
            target.column_by_id(item).name for item in foreign_key.referenced_column_ids
        )
        if foreign_key.source_inheritance_id is not None:
            inheritance = mcd.inheritances[foreign_key.source_inheritance_id]
            parent = mcd.entities[inheritance.parent_entity_id]
            rule = (
                "La stratégie ISA JOINED conserve une table par niveau. La PK de "
                "la table fille est également une FK vers la table mère."
            )
            source = f"Héritage {inheritance.id}, parent {parent.name}"
        else:
            association = mcd.associations[foreign_key.source_association_id]
            relation = (
                mcd.relations.get(foreign_key.source_relation_id)
                if foreign_key.source_relation_id is not None
                else None
            )
            cardinality = (
                f"({relation.cardinality.label})"
                if relation is not None and relation.cardinality is not None
                else "non disponible"
            )
            rule = (
                "L'identifiant de la table référencée migre comme clé étrangère. "
                "Une clé composée reste une seule contrainte FK composée."
            )
            source = f"Association {association.name}, cardinalité {cardinality}"
        return TransformationExplanation(
            f"foreign_key.{foreign_key.id}",
            f"FK vers {target.name}",
            f"{table.name}({local_names}) référence {target.name}({target_names}).",
            rule,
            source,
        )

    def _unique_explanations(
        self, mcd: MCDModel, table: MLDTable
    ) -> list[TransformationExplanation]:
        result: list[TransformationExplanation] = []
        for constraint in table.unique_constraints:
            names = ", ".join(
                table.column_by_id(item).name for item in constraint.column_ids
            )
            association = mcd.associations.get(constraint.source_association_id)
            owner = association or mcd.entities.get(constraint.source_association_id)
            if association is not None and self._is_one_to_one(mcd, association):
                rule = (
                    "Dans une association 1:1, la FK porte UNIQUE afin qu'une "
                    "occurrence référencée ne puisse être associée qu'une fois."
                )
                source = f"Association 1:1 {association.name}"
            else:
                rule = (
                    "L'attribut MCD est déclaré UNIQUE ; cette propriété devient "
                    "une contrainte d'unicité dans le MLD."
                )
                source = (
                    f"{owner.__class__.__name__} {owner.name}"
                    if owner is not None
                    else f"Objet source {constraint.source_association_id}"
                )
            result.append(
                TransformationExplanation(
                    f"unique.{constraint.id}",
                    f"Contrainte UNIQUE ({names})",
                    f"La combinaison ({names}) ne peut apparaître qu'une fois.",
                    rule,
                    source,
                )
            )
        return result

    @staticmethod
    def _check_explanations(
        table: MLDTable,
    ) -> list[TransformationExplanation]:
        return [
            TransformationExplanation(
                f"check.{constraint.id}",
                f"Contrainte CHECK {constraint.name or constraint.id}",
                f"Expression conservée : {constraint.expression}",
                "Une contrainte saisie sur l'attribut MCD est propagée au MLD "
                "sans inventer de règle métier supplémentaire.",
                f"Élément MCD {constraint.source_element_id or 'non renseigné'}",
            )
            for constraint in table.check_constraints
        ]

    @staticmethod
    def _association_relations(
        mcd: MCDModel, association: Association
    ) -> list[Relation]:
        return sorted(
            (
                item
                for item in mcd.relations.values()
                if item.association_id == association.id
            ),
            key=lambda item: item.id,
        )

    @classmethod
    def _is_one_to_one(cls, mcd: MCDModel, association: Association) -> bool:
        relations = cls._association_relations(mcd, association)
        return bool(relations) and all(
            relation.cardinality is not None
            and relation.cardinality.maximum is CardinalityMaximum.ONE
            for relation in relations
        )

    @staticmethod
    def _attribute(mcd: MCDModel, attribute_id: str | None) -> Attribute | None:
        if attribute_id is None:
            return None
        nodes: list[Entity | Association] = [
            *mcd.entities.values(),
            *mcd.associations.values(),
        ]
        for node in nodes:
            for attribute in node.attributes:
                if attribute.id == attribute_id:
                    return attribute
        return None

    @staticmethod
    def _node(mcd: MCDModel, node_id: str | None) -> Entity | Association | None:
        if node_id is None:
            return None
        return mcd.entities.get(node_id) or mcd.associations.get(node_id)

    @staticmethod
    def _node_label(node: Entity | Association | None) -> str:
        if node is None:
            return "Provenance MCD non renseignée"
        return f"{node.__class__.__name__} {node.name} ({node.id})"

    @staticmethod
    def _nullability(column: MLDColumn) -> str:
        if column.nullable is True:
            return "NULL (facultative)"
        if column.nullable is False:
            return "NOT NULL (obligatoire)"
        return "de nullabilité non précisée"
