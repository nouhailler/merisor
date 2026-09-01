"""Comparaison explicable de deux versions d'un modèle MERISE."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from merisor.application.mld_transformer import (
    McdToMldTransformer,
    MLDTransformationError,
)
from merisor.domain import Association, Attribute, Entity, MCDModel, MLDModel


class ChangeKind(str, Enum):
    ADDED = "added"
    MODIFIED = "modified"
    REMOVED = "removed"

    @property
    def symbol(self) -> str:
        return {
            ChangeKind.ADDED: "+",
            ChangeKind.MODIFIED: "~",
            ChangeKind.REMOVED: "-",
        }[self]


@dataclass(frozen=True, slots=True)
class ChangeImpact:
    """Objets dérivés ou dépendants touchés par un changement."""

    associations: tuple[str, ...] = ()
    mld_tables: tuple[str, ...] = ()
    foreign_keys: tuple[str, ...] = ()
    sql_indexes: tuple[str, ...] = ()
    unavailable_reason: str = ""

    @property
    def empty(self) -> bool:
        return not any(
            (self.associations, self.mld_tables, self.foreign_keys, self.sql_indexes)
        )

    def render(self) -> str:
        lines = ["IMPACT DU CHANGEMENT", "=" * 35]
        groups = (
            ("association(s) MCD", self.associations),
            ("table(s) MLD", self.mld_tables),
            ("contrainte(s) FK", self.foreign_keys),
            ("index SQL", self.sql_indexes),
        )
        for label, values in groups:
            lines.append(f"⚠ {len(values)} {label}")
            lines.extend(f"   • {value}" for value in values)
        if self.unavailable_reason:
            lines.extend(("", f"Note : {self.unavailable_reason}"))
        elif self.empty:
            lines.extend(("", "Aucune dépendance directe détectée."))
        return "\n".join(lines)


@dataclass(frozen=True, slots=True)
class VersionChange:
    kind: ChangeKind
    category: str
    path: str
    before: str = ""
    after: str = ""
    source_ids: frozenset[str] = frozenset()
    impact: ChangeImpact = ChangeImpact()

    @property
    def detail(self) -> str:
        if self.kind is ChangeKind.MODIFIED:
            return f"{self.before} → {self.after}"
        return self.after if self.kind is ChangeKind.ADDED else self.before

    def render(self) -> str:
        qualifier = f" [{self.category}]" if self.category else ""
        detail = f" : {self.detail}" if self.detail else ""
        return f"{self.kind.symbol} {self.path}{qualifier}{detail}"


@dataclass(frozen=True, slots=True)
class VersionComparison:
    changes: tuple[VersionChange, ...]
    reference_mld_available: bool
    current_mld_available: bool

    def count(self, kind: ChangeKind) -> int:
        return sum(change.kind is kind for change in self.changes)

    @property
    def identical(self) -> bool:
        return not self.changes

    def render(self) -> str:
        if not self.changes:
            return "Aucune différence : les deux versions sont identiques."
        return "\n".join(change.render() for change in self.changes)

    def render_detailed(self) -> str:
        if not self.changes:
            return self.render()
        sections = ["COMPARAISON DE VERSIONS", "=" * 35]
        for change in self.changes:
            sections.extend(("", change.render(), change.impact.render()))
        return "\n".join(sections)


def _attribute_properties(attribute: Attribute) -> dict[str, str]:
    return {
        "nom": attribute.name,
        "type": attribute.data_type.label if attribute.data_type else "Automatique",
        "identifiant": "oui" if attribute.identifier else "non",
        "nullabilité": (
            "automatique"
            if attribute.nullable is None
            else ("facultatif" if attribute.nullable else "obligatoire")
        ),
        "défaut": attribute.default or "—",
        "unique": "oui" if attribute.unique else "non",
        "auto-incrément": "oui" if attribute.auto_increment else "non",
        "commentaire": attribute.comment or "—",
        "contraintes": "; ".join(attribute.constraints) or "—",
    }


class ModelVersionComparator:
    """Compare la version de référence à l'état courant, sans les modifier."""

    def compare(self, reference: MCDModel, current: MCDModel) -> VersionComparison:
        reference_mld = self._safe_transform(reference)
        current_mld = self._safe_transform(current)
        changes: list[VersionChange] = []
        changes.extend(
            self._compare_nodes(
                "Entité", reference.entities, current.entities, reference, current
            )
        )
        changes.extend(
            self._compare_nodes(
                "Association",
                reference.associations,
                current.associations,
                reference,
                current,
            )
        )
        changes.extend(self._compare_relations(reference, current))
        changes.extend(self._compare_inheritances(reference, current))

        enriched = tuple(
            self._with_impact(
                change,
                reference,
                current,
                reference_mld,
                current_mld,
            )
            for change in sorted(
                changes,
                key=lambda item: (
                    {
                        ChangeKind.REMOVED: 0,
                        ChangeKind.MODIFIED: 1,
                        ChangeKind.ADDED: 2,
                    }[item.kind],
                    item.path.casefold(),
                    item.category.casefold(),
                ),
            )
        )
        return VersionComparison(
            enriched, reference_mld is not None, current_mld is not None
        )

    def _compare_nodes(
        self,
        node_kind: str,
        old: dict[str, Entity] | dict[str, Association],
        new: dict[str, Entity] | dict[str, Association],
        reference: MCDModel,
        current: MCDModel,
    ) -> list[VersionChange]:
        changes: list[VersionChange] = []
        for node_id in old.keys() - new.keys():
            node = old[node_id]
            changes.append(
                VersionChange(
                    ChangeKind.REMOVED,
                    node_kind,
                    node.name,
                    before=node.name,
                    source_ids=frozenset(self._expanded_source_ids(reference, node_id)),
                )
            )
        for node_id in new.keys() - old.keys():
            node = new[node_id]
            changes.append(
                VersionChange(
                    ChangeKind.ADDED,
                    node_kind,
                    node.name,
                    after=node.name,
                    source_ids=frozenset(self._expanded_source_ids(current, node_id)),
                )
            )
        for node_id in old.keys() & new.keys():
            before_node, after_node = old[node_id], new[node_id]
            label = after_node.name or before_node.name
            source_ids = frozenset(
                self._expanded_source_ids(reference, node_id)
                | self._expanded_source_ids(current, node_id)
            )
            if before_node.name != after_node.name:
                changes.append(
                    VersionChange(
                        ChangeKind.MODIFIED,
                        "nom",
                        label,
                        before_node.name,
                        after_node.name,
                        source_ids,
                    )
                )
            if isinstance(before_node, Association) and isinstance(
                after_node, Association
            ):
                association_properties = (
                    (
                        "historisation",
                        str(before_node.is_historized),
                        str(after_node.is_historized),
                    ),
                    (
                        "matérialisation",
                        before_node.materialization_strategy.value,
                        after_node.materialization_strategy.value,
                    ),
                )
                for category, before_value, after_value in association_properties:
                    if before_value != after_value:
                        changes.append(
                            VersionChange(
                                ChangeKind.MODIFIED,
                                category,
                                label,
                                before_value,
                                after_value,
                                source_ids,
                            )
                        )
            changes.extend(
                self._compare_attributes(
                    label,
                    before_node.attributes,
                    after_node.attributes,
                    frozenset((node_id,)),
                )
            )
        return changes

    @staticmethod
    def _compare_attributes(
        owner_name: str,
        old_attributes: list[Attribute],
        new_attributes: list[Attribute],
        owner_source_ids: frozenset[str],
    ) -> list[VersionChange]:
        old = {attribute.id: attribute for attribute in old_attributes}
        new = {attribute.id: attribute for attribute in new_attributes}
        changes: list[VersionChange] = []
        for attribute_id in old.keys() - new.keys():
            attribute = old[attribute_id]
            changes.append(
                VersionChange(
                    ChangeKind.REMOVED,
                    "attribut",
                    f"{owner_name}.{attribute.name}",
                    before=attribute.name,
                    source_ids=frozenset((*owner_source_ids, attribute_id)),
                )
            )
        for attribute_id in new.keys() - old.keys():
            attribute = new[attribute_id]
            changes.append(
                VersionChange(
                    ChangeKind.ADDED,
                    "attribut",
                    f"{owner_name}.{attribute.name}",
                    after=attribute.name,
                    source_ids=frozenset((*owner_source_ids, attribute_id)),
                )
            )
        for attribute_id in old.keys() & new.keys():
            before_attribute, after_attribute = old[attribute_id], new[attribute_id]
            path = f"{owner_name}.{after_attribute.name or before_attribute.name}"
            before_values = _attribute_properties(before_attribute)
            after_values = _attribute_properties(after_attribute)
            for property_name in before_values:
                if before_values[property_name] != after_values[property_name]:
                    changes.append(
                        VersionChange(
                            ChangeKind.MODIFIED,
                            property_name,
                            path,
                            before_values[property_name],
                            after_values[property_name],
                            frozenset((*owner_source_ids, attribute_id)),
                        )
                    )
        return changes

    def _compare_relations(
        self, reference: MCDModel, current: MCDModel
    ) -> list[VersionChange]:
        changes: list[VersionChange] = []
        old, new = reference.relations, current.relations
        for relation_id in old.keys() | new.keys():
            before = old.get(relation_id)
            after = new.get(relation_id)
            relation = after or before
            if relation is None:
                continue
            model = current if after is not None else reference
            entity = model.entities.get(relation.entity_id)
            association = model.associations.get(relation.association_id)
            path = f"{entity.name if entity else '?'} ↔ {association.name if association else '?'}"
            source_ids = frozenset(
                (
                    *self._expanded_source_ids(model, relation.association_id),
                    relation_id,
                )
            )
            if before is None:
                changes.append(
                    VersionChange(
                        ChangeKind.ADDED,
                        "relation",
                        path,
                        after=path,
                        source_ids=source_ids,
                    )
                )
            elif after is None:
                changes.append(
                    VersionChange(
                        ChangeKind.REMOVED,
                        "relation",
                        path,
                        before=path,
                        source_ids=source_ids,
                    )
                )
            else:
                before_signature = self._relation_signature(reference, before)
                after_signature = self._relation_signature(current, after)
                if before_signature != after_signature:
                    changes.append(
                        VersionChange(
                            ChangeKind.MODIFIED,
                            "relation",
                            path,
                            before_signature,
                            after_signature,
                            source_ids,
                        )
                    )
        return changes

    @staticmethod
    def _relation_signature(model: MCDModel, relation: Any) -> str:
        entity = model.entities.get(relation.entity_id)
        association = model.associations.get(relation.association_id)
        cardinality = relation.cardinality.label if relation.cardinality else "?"
        role = f", rôle {relation.role}" if relation.role else ""
        return f"{entity.name if entity else '?'} — {cardinality}{role} — {association.name if association else '?'}"

    def _compare_inheritances(
        self, reference: MCDModel, current: MCDModel
    ) -> list[VersionChange]:
        changes: list[VersionChange] = []
        old, new = reference.inheritances, current.inheritances
        for inheritance_id in old.keys() | new.keys():
            before, after = old.get(inheritance_id), new.get(inheritance_id)
            item = after or before
            if item is None:
                continue
            model = current if after else reference
            parent = model.entities.get(item.parent_entity_id)
            path = f"ISA {parent.name if parent else '?'}"
            source_ids = frozenset(
                (inheritance_id, item.parent_entity_id, *item.child_entity_ids)
            )
            if before is None:
                assert after is not None
                changes.append(
                    VersionChange(
                        ChangeKind.ADDED,
                        "héritage",
                        path,
                        after=after.strategy.value,
                        source_ids=source_ids,
                    )
                )
            elif after is None:
                changes.append(
                    VersionChange(
                        ChangeKind.REMOVED,
                        "héritage",
                        path,
                        before=before.strategy.value,
                        source_ids=source_ids,
                    )
                )
            elif before != after:
                changes.append(
                    VersionChange(
                        ChangeKind.MODIFIED,
                        "héritage",
                        path,
                        before.strategy.value,
                        after.strategy.value,
                        source_ids,
                    )
                )
        return changes

    @staticmethod
    def _safe_transform(model: MCDModel) -> MLDModel | None:
        try:
            return McdToMldTransformer().transform(model)
        except (MLDTransformationError, ValueError, KeyError):
            return None

    @staticmethod
    def _expanded_source_ids(model: MCDModel, source_id: str) -> set[str]:
        ids = {source_id}
        entity = model.entities.get(source_id)
        if entity is not None:
            ids.update(attribute.id for attribute in entity.attributes)
            relations = [
                relation
                for relation in model.relations.values()
                if relation.entity_id == source_id
            ]
            ids.update(relation.id for relation in relations)
            ids.update(relation.association_id for relation in relations)
        association = model.associations.get(source_id)
        if association is not None:
            ids.update(attribute.id for attribute in association.attributes)
            ids.update(
                relation.id
                for relation in model.relations.values()
                if relation.association_id == source_id
            )
        return ids

    def _with_impact(
        self,
        change: VersionChange,
        reference: MCDModel,
        current: MCDModel,
        reference_mld: MLDModel | None,
        current_mld: MLDModel | None,
    ) -> VersionChange:
        model = current if change.kind is ChangeKind.ADDED else reference
        mld = current_mld if change.kind is ChangeKind.ADDED else reference_mld
        association_names = sorted(
            {
                association.name
                for association in model.associations.values()
                if association.id in change.source_ids
            },
            key=str.casefold,
        )
        if mld is None:
            impact = ChangeImpact(
                associations=tuple(association_names),
                unavailable_reason=(
                    "Le MLD de cette version ne peut pas être construit ; "
                    "les impacts MLD/SQL ne sont donc pas chiffrables."
                ),
            )
        else:
            impact = self._mld_impact(mld, change.source_ids, association_names)
        return VersionChange(
            change.kind,
            change.category,
            change.path,
            change.before,
            change.after,
            change.source_ids,
            impact,
        )

    @staticmethod
    def _mld_impact(
        mld: MLDModel, source_ids: frozenset[str], association_names: list[str]
    ) -> ChangeImpact:
        affected_table_ids: set[str] = set()
        for table in mld.tables:
            if table.source_element_id in source_ids or any(
                column.source_attribute_id in source_ids
                or column.source_element_id in source_ids
                or column.source_relation_id in source_ids
                for column in table.columns
            ):
                affected_table_ids.add(table.id)
            if any(
                foreign_key.source_association_id in source_ids
                or foreign_key.source_relation_id in source_ids
                or foreign_key.source_inheritance_id in source_ids
                for foreign_key in table.foreign_keys
            ):
                affected_table_ids.add(table.id)

        foreign_keys: list[str] = []
        indexes: list[str] = []
        for table in mld.tables:
            for foreign_key in table.foreign_keys:
                if (
                    table.id in affected_table_ids
                    or foreign_key.referenced_table_id in affected_table_ids
                    or foreign_key.source_association_id in source_ids
                    or foreign_key.source_relation_id in source_ids
                    or foreign_key.source_inheritance_id in source_ids
                ):
                    foreign_keys.append(
                        f"{table.name}.{foreign_key.name or foreign_key.id}"
                    )
            if table.id in affected_table_ids:
                indexes.extend(f"{table.name}.{index.name}" for index in table.indexes)
        table_names = sorted(
            (table.name for table in mld.tables if table.id in affected_table_ids),
            key=str.casefold,
        )
        return ChangeImpact(
            tuple(association_names),
            tuple(table_names),
            tuple(sorted(foreign_keys, key=str.casefold)),
            tuple(sorted(indexes, key=str.casefold)),
        )
