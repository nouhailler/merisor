"""Transformation déterministe d'un MCD MERISE validé vers un MLD."""

from __future__ import annotations

import hashlib
import json

from merisor.domain import (
    Association,
    Attribute,
    CardinalityMaximum,
    CardinalityMinimum,
    Entity,
    MCDModel,
    MLDColumn,
    MLDDataType,
    MLDDataTypeName,
    MLDForeignKey,
    MLDModel,
    MLDTable,
    MLDTableSource,
    MLDUniqueConstraint,
    MaterializationStrategy,
    Relation,
)


class MLDTransformationError(ValueError):
    """Le MCD est valide en V0.2 mais utilise une règle non prise en charge."""

    def __init__(self, problems: str | list[str]) -> None:
        self.problems = (
            (problems,) if isinstance(problems, str) else tuple(problems)
        )
        super().__init__("\n".join(self.problems))


class MLDNamePolicy:
    """Couche de nommage logique, sans normalisation spécifique à un SGBD.

    Les noms source sont conservés. En cas de collision induite par deux FK ou
    par un attribut d'association migré, un suffixe source stable est ajouté.
    """

    @staticmethod
    def table_name(source_name: str) -> str:
        return source_name

    @staticmethod
    def attribute_column_name(source_name: str) -> str:
        return source_name

    @staticmethod
    def technical_identifier_name(source_name: str) -> str:
        """Nom logique stable ; aucune normalisation SQL n'est appliquée."""

        return f"id_{source_name.strip().casefold()}"

    def allocate(
        self,
        preferred: str,
        used_names: set[str],
        *stable_suffixes: str,
    ) -> str:
        candidates = [preferred]
        candidates.extend(
            f"{preferred}_{suffix}" for suffix in stable_suffixes if suffix
        )
        for candidate in candidates:
            key = candidate.casefold()
            if key not in used_names:
                used_names.add(key)
                return candidate
        index = 2
        base = candidates[-1]
        while f"{base}_{index}".casefold() in used_names:
            index += 1
        result = f"{base}_{index}"
        used_names.add(result.casefold())
        return result


def mcd_logical_fingerprint(model: MCDModel) -> str:
    """Empreinte du contenu MCD pertinent pour le MLD, positions exclues."""

    def attributes(items: list[Attribute]) -> list[dict[str, object]]:
        return [
            {
                "id": attribute.id,
                "name": attribute.name,
                "identifier": attribute.identifier,
            }
            for attribute in items
        ]

    data = {
        "entities": [
            {
                "id": entity.id,
                "name": entity.name,
                "attributes": attributes(entity.attributes),
            }
            for entity in sorted(model.entities.values(), key=lambda item: item.id)
        ],
        "associations": [
            {
                "id": association.id,
                "name": association.name,
                "attributes": attributes(association.attributes),
                "is_historized": association.is_historized,
                "materialization_strategy": (
                    association.materialization_strategy.value
                ),
            }
            for association in sorted(
                model.associations.values(), key=lambda item: item.id
            )
        ],
        "relations": [
            {
                "id": relation.id,
                "entity_id": relation.entity_id,
                "association_id": relation.association_id,
                "cardinality": (
                    None
                    if relation.cardinality is None
                    else {
                        "minimum": relation.cardinality.minimum.value,
                        "maximum": relation.cardinality.maximum.value,
                    }
                ),
            }
            for relation in sorted(model.relations.values(), key=lambda item: item.id)
        ],
    }
    payload = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class McdToMldTransformer:
    """Applique les règles binaires V0.3 sans modifier le MCD source.

    FORCE_TABLE et l'historisation matérialisent les associations non-N:N.
    FORCE_FK conserve les règles classiques lorsqu'elles sont compatibles.
    Une association N:N conserve sa table et sa PK composée historique.

    Décision 1:N : conformément aux exemples normatifs des sections 12, 13 et
    20, la table de l'entité dont le maximum vaut 1 porte la FK vers l'entité
    dont le maximum vaut N. La nullabilité dépend du minimum du côté N.

    Décision 1:1 symétrique : si les deux minima sont identiques, la table
    porteuse est la première selon (nom insensible à la casse, identifiant).
    """

    def __init__(self, name_policy: MLDNamePolicy | None = None) -> None:
        self.name_policy = name_policy or MLDNamePolicy()

    def transform(self, model: MCDModel) -> MLDModel:
        tables_by_entity: dict[str, MLDTable] = {}
        for entity in sorted(model.entities.values(), key=self._node_sort_key):
            table = self._entity_table(entity)
            tables_by_entity[entity.id] = table

        generated_tables: list[MLDTable] = list(tables_by_entity.values())
        for association in sorted(
            model.associations.values(), key=self._node_sort_key
        ):
            relations = sorted(
                (
                    relation
                    for relation in model.relations.values()
                    if relation.association_id == association.id
                ),
                key=lambda relation: self._relation_sort_key(model, relation),
            )
            self._check_binary_association(model, association, relations)
            # Les cardinalités sont garanties présentes par le contrôle ci-dessus.
            maxima = [relation.cardinality.maximum for relation in relations]
            is_many_to_many = all(
                maximum is CardinalityMaximum.MANY for maximum in maxima
            )
            if (
                association.is_historized
                and association.materialization_strategy
                is MaterializationStrategy.FORCE_FK
            ):
                raise MLDTransformationError(
                    f"L'association {association.name} est historisée mais utilise "
                    "FORCE_FK. Une association historisée doit être matérialisée "
                    "en table ; utilisez AUTO ou FORCE_TABLE."
                )
            if (
                is_many_to_many
                and association.materialization_strategy
                is MaterializationStrategy.FORCE_FK
            ):
                raise MLDTransformationError(
                    f"L'association {association.name} est de type N:N. "
                    "La stratégie FORCE_FK est incompatible avec une relation N:N."
                )
            if is_many_to_many:
                generated_tables.append(
                    self._transform_many_to_many(
                        model, association, relations, tables_by_entity
                    )
                )
            elif (
                association.materialization_strategy
                is MaterializationStrategy.FORCE_TABLE
                or association.is_historized
            ):
                generated_tables.append(
                    self._transform_materialized_association(
                        model, association, relations, tables_by_entity
                    )
                )
            elif all(maximum is CardinalityMaximum.ONE for maximum in maxima):
                self._transform_one_to_one(
                    model, association, relations, tables_by_entity
                )
            else:
                self._transform_one_to_many(
                    model, association, relations, tables_by_entity
                )

        generated_tables.sort(
            key=lambda table: (table.name.casefold(), table.id)
        )
        return MLDModel(
            tables=generated_tables,
            generated_from_fingerprint=mcd_logical_fingerprint(model),
        )

    @staticmethod
    def _node_sort_key(node: Entity | Association) -> tuple[str, str]:
        return node.name.casefold(), node.id

    def _relation_sort_key(
        self, model: MCDModel, relation: Relation
    ) -> tuple[str, str]:
        entity = model.entities[relation.entity_id]
        return entity.name.casefold(), entity.id

    def _entity_table(self, entity: Entity) -> MLDTable:
        if not entity.identifier_attributes:
            raise MLDTransformationError(
                f"L'entité {entity.name} ne possède aucun identifiant."
            )
        columns = [
            MLDColumn(
                id=self._attribute_column_id(attribute),
                name=self.name_policy.attribute_column_name(attribute.name),
                nullable=False if attribute.identifier else None,
                data_type=self._attribute_data_type(attribute),
                source_attribute_id=attribute.id,
                source_element_id=entity.id,
            )
            for attribute in entity.attributes
        ]
        primary_key = tuple(
            self._attribute_column_id(attribute)
            for attribute in entity.identifier_attributes
        )
        return MLDTable(
            id=self._entity_table_id(entity.id),
            name=self.name_policy.table_name(entity.name),
            source_element_id=entity.id,
            source=MLDTableSource.ENTITY,
            columns=columns,
            primary_key=primary_key,
        )

    def _check_binary_association(
        self,
        model: MCDModel,
        association: Association,
        relations: list[Relation],
    ) -> None:
        if len(relations) > 2:
            raise MLDTransformationError(
                f"L'association {association.name} implique {len(relations)} entités. "
                "Les associations ternaires ou de degré supérieur ne sont pas supportées."
            )
        if len(relations) < 2:
            raise MLDTransformationError(
                f"L'association {association.name} doit relier exactement deux entités."
            )
        if len({relation.entity_id for relation in relations}) != 2:
            raise MLDTransformationError(
                f"L'association réflexive {association.name} n'est pas supportée en V0.3."
            )
        if any(relation.cardinality is None for relation in relations):
            raise MLDTransformationError(
                f"L'association {association.name} possède une cardinalité manquante."
            )
        if any(relation.entity_id not in model.entities for relation in relations):
            raise MLDTransformationError(
                f"L'association {association.name} référence une entité inconnue."
            )

    def _transform_many_to_many(
        self,
        model: MCDModel,
        association: Association,
        relations: list[Relation],
        entity_tables: dict[str, MLDTable],
    ) -> MLDTable:
        table = MLDTable(
            id=self._association_table_id(association.id),
            name=self.name_policy.table_name(association.name),
            source_element_id=association.id,
            source=MLDTableSource.ASSOCIATION,
            is_historized=association.is_historized,
        )
        used_names: set[str] = set()
        primary_key: list[str] = []
        has_explicit_identifier = bool(association.identifier_attributes)
        if has_explicit_identifier:
            self._append_association_attributes(
                table,
                association,
                used_names,
                nullable=False,
                identifier_filter=True,
            )
            primary_key.extend(
                self._attribute_column_id(attribute)
                for attribute in association.identifier_attributes
            )
        for relation in relations:
            source_entity = model.entities[relation.entity_id]
            referenced_table = entity_tables[source_entity.id]
            column_ids, referenced_column_ids = self._migrate_primary_key(
                table,
                referenced_table,
                source_entity,
                association,
                relation,
                nullable=False,
                used_names=used_names,
            )
            if not has_explicit_identifier:
                primary_key.extend(column_ids)
            table.foreign_keys.append(
                MLDForeignKey(
                    id=self._foreign_key_id(
                        association.id, table.source_element_id, source_entity.id
                    ),
                    column_ids=column_ids,
                    referenced_table_id=referenced_table.id,
                    referenced_column_ids=referenced_column_ids,
                    source_association_id=association.id,
                    source_relation_id=relation.id,
                    source_cardinality=self._source_cardinality(relation),
                )
            )
        table.primary_key = tuple(primary_key)
        self._append_association_attributes(
            table,
            association,
            used_names,
            nullable=None,
            identifier_filter=False if has_explicit_identifier else None,
        )
        return table

    def _transform_materialized_association(
        self,
        model: MCDModel,
        association: Association,
        relations: list[Relation],
        entity_tables: dict[str, MLDTable],
    ) -> MLDTable:
        """Crée une table d'occurrences distinctes pour une association non-N:N."""

        table = MLDTable(
            id=self._association_table_id(association.id),
            name=self.name_policy.table_name(association.name),
            source_element_id=association.id,
            source=MLDTableSource.ASSOCIATION,
            is_historized=association.is_historized,
        )
        used_names: set[str] = set()
        if association.identifier_attributes:
            self._append_association_attributes(
                table,
                association,
                used_names,
                nullable=False,
                identifier_filter=True,
            )
            table.primary_key = tuple(
                self._attribute_column_id(attribute)
                for attribute in association.identifier_attributes
            )
        else:
            technical_column_id = self._technical_identifier_column_id(
                association.id
            )
            technical_name = self.name_policy.allocate(
                self.name_policy.technical_identifier_name(association.name),
                used_names,
                association.name,
            )
            table.columns.append(
                MLDColumn(
                    id=technical_column_id,
                    name=technical_name,
                    nullable=False,
                    data_type=MLDDataType(MLDDataTypeName.INTEGER),
                    source_element_id=association.id,
                    generated=True,
                    auto_increment=True,
                )
            )
            table.primary_key = (technical_column_id,)

        for relation in relations:
            source_entity = model.entities[relation.entity_id]
            referenced_table = entity_tables[source_entity.id]
            nullable = relation.cardinality.minimum is CardinalityMinimum.ZERO
            column_ids, referenced_column_ids = self._migrate_primary_key(
                table,
                referenced_table,
                source_entity,
                association,
                relation,
                nullable=nullable,
                used_names=used_names,
            )
            table.foreign_keys.append(
                MLDForeignKey(
                    id=self._foreign_key_id(
                        association.id, association.id, source_entity.id
                    ),
                    column_ids=column_ids,
                    referenced_table_id=referenced_table.id,
                    referenced_column_ids=referenced_column_ids,
                    source_association_id=association.id,
                    source_relation_id=relation.id,
                    source_cardinality=self._source_cardinality(relation),
                )
            )

        self._append_association_attributes(
            table,
            association,
            used_names,
            nullable=None,
            identifier_filter=(
                False if association.identifier_attributes else None
            ),
        )
        return table

    def _transform_one_to_many(
        self,
        model: MCDModel,
        association: Association,
        relations: list[Relation],
        entity_tables: dict[str, MLDTable],
    ) -> None:
        many_relation = next(
            relation
            for relation in relations
            if relation.cardinality.maximum is CardinalityMaximum.MANY
        )
        one_relation = next(
            relation
            for relation in relations
            if relation.cardinality.maximum is CardinalityMaximum.ONE
        )
        referenced_entity = model.entities[many_relation.entity_id]
        holder_entity = model.entities[one_relation.entity_id]
        referenced_table = entity_tables[referenced_entity.id]
        holder_table = entity_tables[holder_entity.id]
        used_names = {column.name.casefold() for column in holder_table.columns}
        nullable = many_relation.cardinality.minimum is CardinalityMinimum.ZERO
        column_ids, referenced_column_ids = self._migrate_primary_key(
            holder_table,
            referenced_table,
            referenced_entity,
            association,
            many_relation,
            nullable=nullable,
            used_names=used_names,
        )
        holder_table.foreign_keys.append(
            MLDForeignKey(
                id=self._foreign_key_id(
                    association.id, holder_entity.id, referenced_entity.id
                ),
                column_ids=column_ids,
                referenced_table_id=referenced_table.id,
                referenced_column_ids=referenced_column_ids,
                source_association_id=association.id,
                source_relation_id=many_relation.id,
                source_cardinality=self._source_cardinality(many_relation),
            )
        )
        self._append_association_attributes(
            holder_table, association, used_names, nullable=None
        )

    def _transform_one_to_one(
        self,
        model: MCDModel,
        association: Association,
        relations: list[Relation],
        entity_tables: dict[str, MLDTable],
    ) -> None:
        if association.attributes:
            raise MLDTransformationError(
                f"L'association 1:1 {association.name} porte des attributs. "
                "Ce cas n'est pas transformé automatiquement en V0.3."
            )
        holder_relation, referenced_relation = self._one_to_one_sides(
            model, relations
        )
        holder_entity = model.entities[holder_relation.entity_id]
        referenced_entity = model.entities[referenced_relation.entity_id]
        holder_table = entity_tables[holder_entity.id]
        referenced_table = entity_tables[referenced_entity.id]
        used_names = {column.name.casefold() for column in holder_table.columns}
        nullable = holder_relation.cardinality.minimum is CardinalityMinimum.ZERO
        column_ids, referenced_column_ids = self._migrate_primary_key(
            holder_table,
            referenced_table,
            referenced_entity,
            association,
            referenced_relation,
            nullable=nullable,
            used_names=used_names,
        )
        holder_table.foreign_keys.append(
            MLDForeignKey(
                id=self._foreign_key_id(
                    association.id, holder_entity.id, referenced_entity.id
                ),
                column_ids=column_ids,
                referenced_table_id=referenced_table.id,
                referenced_column_ids=referenced_column_ids,
                source_association_id=association.id,
                source_relation_id=holder_relation.id,
                source_cardinality=self._source_cardinality(holder_relation),
            )
        )
        holder_table.unique_constraints.append(
            MLDUniqueConstraint(
                id=f"unique:{association.id}:{holder_entity.id}",
                column_ids=column_ids,
                source_association_id=association.id,
            )
        )

    def _one_to_one_sides(
        self, model: MCDModel, relations: list[Relation]
    ) -> tuple[Relation, Relation]:
        mandatory = [
            relation
            for relation in relations
            if relation.cardinality.minimum is CardinalityMinimum.ONE
        ]
        if len(mandatory) == 1:
            holder = mandatory[0]
            referenced = next(item for item in relations if item is not holder)
            return holder, referenced
        ordered = sorted(
            relations,
            key=lambda relation: self._relation_sort_key(model, relation),
        )
        return ordered[0], ordered[1]

    def _migrate_primary_key(
        self,
        holder_table: MLDTable,
        referenced_table: MLDTable,
        referenced_entity: Entity,
        association: Association,
        relation: Relation,
        *,
        nullable: bool,
        used_names: set[str],
    ) -> tuple[tuple[str, ...], tuple[str, ...]]:
        local_ids: list[str] = []
        referenced_ids: list[str] = []
        for index, source_attribute in enumerate(
            referenced_entity.identifier_attributes
        ):
            referenced_column_id = referenced_table.primary_key[index]
            referenced_column = referenced_table.column_by_id(
                referenced_column_id
            )
            name = self.name_policy.allocate(
                source_attribute.name,
                used_names,
                referenced_entity.name,
                association.name,
            )
            column_id = (
                f"column:fk:{association.id}:{holder_table.source_element_id}:"
                f"{source_attribute.id}"
            )
            holder_table.columns.append(
                MLDColumn(
                    id=column_id,
                    name=name,
                    nullable=nullable,
                    data_type=referenced_column.data_type,
                    source_attribute_id=source_attribute.id,
                    source_element_id=referenced_entity.id,
                    source_relation_id=relation.id,
                    generated=True,
                )
            )
            local_ids.append(column_id)
            referenced_ids.append(referenced_column_id)
        return tuple(local_ids), tuple(referenced_ids)

    def _append_association_attributes(
        self,
        table: MLDTable,
        association: Association,
        used_names: set[str],
        *,
        nullable: bool | None,
        identifier_filter: bool | None = None,
    ) -> None:
        for attribute in association.attributes:
            if (
                identifier_filter is not None
                and attribute.identifier is not identifier_filter
            ):
                continue
            name = self.name_policy.allocate(
                attribute.name, used_names, association.name
            )
            table.columns.append(
                MLDColumn(
                    id=self._attribute_column_id(attribute),
                    name=name,
                    nullable=nullable,
                    data_type=self._attribute_data_type(attribute),
                    source_attribute_id=attribute.id,
                    source_element_id=association.id,
                )
            )

    @staticmethod
    def _attribute_column_id(attribute: Attribute) -> str:
        return f"column:attribute:{attribute.id}"

    @staticmethod
    def _attribute_data_type(attribute: Attribute) -> MLDDataType:
        """Valeur V0.4 par défaut tant que le MCD ne porte pas de type."""

        if attribute.identifier:
            return MLDDataType(MLDDataTypeName.INTEGER)
        return MLDDataType.varchar(100)

    @staticmethod
    def _technical_identifier_column_id(association_id: str) -> str:
        return f"column:technical:{association_id}:identifier"

    @staticmethod
    def _source_cardinality(relation: Relation) -> tuple[str, str]:
        if relation.cardinality is None:
            raise MLDTransformationError(
                "Une relation sans cardinalité ne peut pas produire de FK."
            )
        return (
            relation.cardinality.minimum.value,
            relation.cardinality.maximum.value,
        )

    @staticmethod
    def _entity_table_id(entity_id: str) -> str:
        return f"table:entity:{entity_id}"

    @staticmethod
    def _association_table_id(association_id: str) -> str:
        return f"table:association:{association_id}"

    @staticmethod
    def _foreign_key_id(
        association_id: str, holder_id: str, referenced_id: str
    ) -> str:
        return f"fk:{association_id}:{holder_id}:{referenced_id}"
