"""Traçabilité déterministe d'un élément MLD jusqu'au MCD et au SQL."""

from __future__ import annotations

from dataclasses import dataclass

from merisor.domain import (
    Association,
    Attribute,
    Entity,
    MCDModel,
    MLDColumn,
    MLDForeignKey,
    MLDModel,
    MLDTable,
)

from .sql_generator import SQLDialect, SQLTarget, sql_dialect


@dataclass(frozen=True, slots=True)
class TraceabilityReport:
    """Chaîne pédagogique complète pour une table ou une colonne MLD."""

    target_label: str
    mcd_path: tuple[str, ...]
    mld_path: tuple[str, ...]
    origin: str
    transformation: str
    consequence: str
    sql_target: SQLTarget
    sql: str

    def render_text(self) -> str:
        return "\n\n".join(
            (
                f"TRAÇABILITÉ — {self.target_label}",
                "ORIGINE\n" + self.origin,
                "TRANSFORMATION\n" + self.transformation,
                "CONSÉQUENCE\n" + self.consequence,
                f"SQL — {self.sql_target.display_name}\n{self.sql}",
            )
        )


class ModelTraceabilityService:
    """Explique la provenance sans IA et sans analyser le SQL généré."""

    def trace(
        self,
        mcd: MCDModel,
        mld: MLDModel,
        table: MLDTable,
        column_id: str | None = None,
        target: SQLTarget | str = SQLTarget.POSTGRESQL,
    ) -> TraceabilityReport:
        mld.table_by_id(table.id)
        sql_target = SQLTarget(target)
        column = table.column_by_id(column_id) if column_id is not None else None
        owner, attribute = self._source(mcd, table, column)
        mcd_path = self._mcd_path(owner, attribute)
        mld_path = (table.name,) + ((column.name,) if column is not None else ())
        return TraceabilityReport(
            target_label=(
                f"{table.name}.{column.name}" if column is not None else table.name
            ),
            mcd_path=mcd_path,
            mld_path=mld_path,
            origin=self._origin(table, column, owner, attribute),
            transformation=self._transformation(mcd, table, column),
            consequence=self._consequence(mld, table, column),
            sql_target=sql_target,
            sql=self._sql_snippet(mld, table, column, sql_target),
        )

    @staticmethod
    def _source(
        mcd: MCDModel, table: MLDTable, column: MLDColumn | None
    ) -> tuple[Entity | Association | None, Attribute | None]:
        element_id = column.source_element_id if column is not None else None
        owner = (
            mcd.entities.get(element_id or "")
            or mcd.associations.get(element_id or "")
            or mcd.entities.get(table.source_element_id)
            or mcd.associations.get(table.source_element_id)
        )
        attribute_id = column.source_attribute_id if column is not None else None
        attribute = None
        if attribute_id is not None:
            for entity in mcd.entities.values():
                attribute = next(
                    (item for item in entity.attributes if item.id == attribute_id),
                    None,
                )
                if attribute is not None:
                    owner = entity
                    break
            if attribute is None:
                for association in mcd.associations.values():
                    attribute = next(
                        (
                            item
                            for item in association.attributes
                            if item.id == attribute_id
                        ),
                        None,
                    )
                    if attribute is not None:
                        owner = association
                        break
        return owner, attribute

    @staticmethod
    def _mcd_path(
        owner: Entity | Association | None, attribute: Attribute | None
    ) -> tuple[str, ...]:
        if owner is None:
            return ("Origine technique",)
        kind = "Entité" if isinstance(owner, Entity) else "Association"
        path = (f"{kind} {owner.name}",)
        return path + ((attribute.name,) if attribute is not None else ())

    @staticmethod
    def _origin(
        table: MLDTable,
        column: MLDColumn | None,
        owner: Entity | Association | None,
        attribute: Attribute | None,
    ) -> str:
        if column is not None and attribute is not None and owner is not None:
            return f"MCD → {owner.name}.{attribute.name} ({attribute.id})"
        if column is not None and column.generated:
            return (
                f"MCD → {owner.name if owner is not None else table.name}\n"
                "Aucun attribut MCD direct : colonne générée par la transformation."
            )
        return (
            f"MCD → {owner.name} ({owner.id})"
            if owner is not None
            else "La provenance MCD n'est pas disponible."
        )

    def _transformation(
        self, mcd: MCDModel, table: MLDTable, column: MLDColumn | None
    ) -> str:
        if column is None:
            source = mcd.entities.get(table.source_element_id)
            if source is not None:
                return (
                    f"L'entité {source.name} devient la table {table.name}. "
                    "Ses attributs deviennent des colonnes et son identifiant la PK."
                )
            association = mcd.associations.get(table.source_element_id)
            return (
                f"L'association {association.name if association else table.name} "
                "est matérialisée en table selon ses cardinalités ou sa stratégie."
            )
        if column.source_relation_id is not None:
            relation = mcd.relations[column.source_relation_id]
            association = mcd.associations[relation.association_id]
            branches = []
            for branch in sorted(
                mcd.connected_relations(association.id), key=lambda item: item.id
            ):
                entity = mcd.entities[branch.entity_id]
                cardinality = (
                    f"({branch.cardinality.label})"
                    if branch.cardinality is not None
                    else "(inconnue)"
                )
                role = f", rôle {branch.role}" if branch.role else ""
                branches.append(f"{entity.name} {cardinality}{role}")
            return (
                f"Association {association.name}\nCardinalités : "
                + " / ".join(branches)
                + "\nL'identifiant de l'entité référencée migre dans la table "
                f"{table.name}."
            )
        if column.generated:
            return (
                "MERISOR génère cette colonne technique pour préserver "
                "l'identification du modèle logique."
            )
        if table.is_primary_key(column.id):
            return "L'attribut identifiant du MCD devient une colonne de clé primaire."
        return "L'attribut du MCD devient une colonne du MLD en conservant son type."

    @staticmethod
    def _consequence(mld: MLDModel, table: MLDTable, column: MLDColumn | None) -> str:
        if column is None:
            return (
                f"Création de la table {table.name} avec {len(table.columns)} colonne(s), "
                f"{len(table.foreign_keys)} FK et une PK de "
                f"{len(table.primary_key)} colonne(s)."
            )
        roles = []
        if table.is_primary_key(column.id):
            roles.append("membre de la clé primaire")
        foreign_keys = [
            key for key in table.foreign_keys if column.id in key.column_ids
        ]
        for key in foreign_keys:
            target = mld.table_by_id(key.referenced_table_id)
            roles.append(f"création d'une FK dans {table.name} vers {target.name}")
        if table.is_unique(column.id):
            roles.append("contrainte UNIQUE")
        roles.append("NOT NULL" if column.nullable is False else "NULL autorisé")
        return "; ".join(roles) + "."

    def _sql_snippet(
        self,
        mld: MLDModel,
        table: MLDTable,
        column: MLDColumn | None,
        target: SQLTarget,
    ) -> str:
        dialect = sql_dialect(target)
        selected_ids = (
            {item.id for item in table.columns} if column is None else {column.id}
        )
        if column is not None and column.id in table.primary_key:
            selected_ids.update(table.primary_key)
        for foreign_key in table.foreign_keys:
            if column is None or selected_ids.intersection(foreign_key.column_ids):
                selected_ids.update(foreign_key.column_ids)
        for constraint in table.unique_constraints:
            if column is None or selected_ids.intersection(constraint.column_ids):
                selected_ids.update(constraint.column_ids)
        selected_columns = [item for item in table.columns if item.id in selected_ids]
        inline_pk = dialect.uses_inline_auto_primary_key(table)
        definitions = [
            dialect.render_column(
                item,
                inline_auto_primary_key=(inline_pk and table.primary_key == (item.id,)),
            )
            for item in selected_columns
        ]
        if (
            table.primary_key
            and (column is None or column.id in table.primary_key)
            and not inline_pk
        ):
            definitions.append(
                "PRIMARY KEY ("
                + self._column_names(table, table.primary_key, dialect)
                + ")"
            )
        for foreign_key in table.foreign_keys:
            if selected_ids.intersection(foreign_key.column_ids):
                definitions.append(
                    self._foreign_key_clause(mld, table, foreign_key, dialect)
                )
        for constraint in table.unique_constraints:
            if selected_ids.intersection(constraint.column_ids):
                definitions.append(
                    "UNIQUE ("
                    + self._column_names(table, constraint.column_ids, dialect)
                    + ")"
                )
        body = ",\n".join(f"    {definition}" for definition in definitions)
        return f"CREATE TABLE {dialect.quote_identifier(table.name)} (\n{body}\n);"

    def _foreign_key_clause(
        self,
        mld: MLDModel,
        table: MLDTable,
        foreign_key: MLDForeignKey,
        dialect: SQLDialect,
    ) -> str:
        target = mld.table_by_id(foreign_key.referenced_table_id)
        clause = (
            "FOREIGN KEY ("
            + self._column_names(table, foreign_key.column_ids, dialect)
            + f") REFERENCES {dialect.quote_identifier(target.name)} ("
            + self._column_names(target, foreign_key.referenced_column_ids, dialect)
            + ")"
        )
        if foreign_key.on_delete is not None:
            clause += f" ON DELETE {foreign_key.on_delete.value}"
        if foreign_key.on_update is not None:
            clause += f" ON UPDATE {foreign_key.on_update.value}"
        return clause

    @staticmethod
    def _column_names(
        table: MLDTable, ids: tuple[str, ...], dialect: SQLDialect
    ) -> str:
        return ", ".join(
            dialect.quote_identifier(table.column_by_id(column_id).name)
            for column_id in ids
        )
