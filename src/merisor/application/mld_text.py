"""Représentation textuelle stable d'un modèle MLD."""

from __future__ import annotations

from merisor.domain import MLDModel, MLDTable


def render_mld_text(model: MLDModel) -> str:
    """Produit un texte lisible, déterministe et indépendant de SQL."""

    sections = [_render_table(model, table) for table in model.tables]
    return "\n\n".join(sections) + ("\n" if sections else "")


def _render_table(model: MLDModel, table: MLDTable) -> str:
    lines = [table.name]
    if table.is_historized:
        lines.append("[Association historisée]")
    lines.append("-" * max(6, len(table.name)))
    for column in table.columns:
        roles: list[str] = []
        if table.is_primary_key(column.id):
            roles.append("PK")
        if table.is_foreign_key(column.id):
            roles.append("FK")
        if table.is_unique(column.id):
            roles.append("UNIQUE")
        if column.auto_increment:
            roles.append("AUTO")
        if column.nullable is True:
            roles.append("NULL")
        elif column.nullable is False:
            roles.append("NOT NULL")
        prefix = "/".join(roles) if roles else ""
        lines.append(
            f"{prefix:<18} {column.name} : {column.data_type.label}".rstrip()
        )

    for foreign_key in table.foreign_keys:
        local_names = ", ".join(
            table.column_by_id(column_id).name
            for column_id in foreign_key.column_ids
        )
        referenced_table = model.table_by_id(foreign_key.referenced_table_id)
        referenced_names = ", ".join(
            referenced_table.column_by_id(column_id).name
            for column_id in foreign_key.referenced_column_ids
        )
        lines.append(
            f"FK ({local_names}) → {referenced_table.name}({referenced_names})"
        )
    for constraint in table.unique_constraints:
        names = ", ".join(
            table.column_by_id(column_id).name
            for column_id in constraint.column_ids
        )
        lines.append(f"UNIQUE ({names})")
    return "\n".join(lines)
