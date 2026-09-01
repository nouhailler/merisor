"""Génération déterministe d'une documentation MCD/MLD complète."""

from __future__ import annotations

import html
from dataclasses import dataclass

from merisor import __version__
from merisor.application.diagram_text_exporter import DiagramTextExporter
from merisor.application.mld_transformer import (
    McdToMldTransformer,
    MLDTransformationError,
)
from merisor.domain import Association, Attribute, Entity, MCDModel, MLDModel, MLDTable
from merisor.domain.validation import validate_mcd


@dataclass(frozen=True, slots=True)
class ModelDocumentation:
    """Les deux représentations d'une même documentation générée."""

    title: str
    markdown: str
    html: str
    warnings: tuple[str, ...]
    includes_mld: bool


class ModelDocumentationGenerator:
    """Documente le modèle sans inférer de sémantique absente du MCD."""

    def generate(
        self,
        model: MCDModel,
        *,
        project_name: str = "Projet MERISOR",
        mld: MLDModel | None = None,
        mcd_image_data_uri: str | None = None,
        mld_image_data_uri: str | None = None,
    ) -> ModelDocumentation:
        warnings: list[str] = []
        logical_model = mld
        if logical_model is None:
            report = validate_mcd(model)
            if report.errors:
                warnings.append(
                    "Le MCD contient des erreurs bloquantes : la partie MLD "
                    "n'a pas pu être générée."
                )
            else:
                try:
                    logical_model = McdToMldTransformer().transform(model)
                except (MLDTransformationError, ValueError, KeyError) as error:
                    warnings.append(f"MLD indisponible : {error}")

        title = f"Documentation — {project_name}"
        markdown = self._markdown(model, logical_model, title, warnings)
        html_text = self._html(
            model,
            logical_model,
            title,
            warnings,
            mcd_image_data_uri,
            mld_image_data_uri,
        )
        return ModelDocumentation(
            title=title,
            markdown=markdown,
            html=html_text,
            warnings=tuple(warnings),
            includes_mld=logical_model is not None,
        )

    def _markdown(
        self,
        model: MCDModel,
        mld: MLDModel | None,
        title: str,
        warnings: list[str],
    ) -> str:
        lines = [f"# {title}", "", f"*Généré par MERISOR {__version__}.*", ""]
        if warnings:
            lines.extend(("> [!WARNING]", *[f"> {item}" for item in warnings], ""))
        lines.extend(
            (
                "## Modèle conceptuel",
                "",
                "### Diagramme",
                "",
                "```mermaid",
                DiagramTextExporter().render_mcd_mermaid(model).rstrip(),
                "```",
                "",
                "### Entités",
                "",
            )
        )
        for entity in self._entities(model):
            lines.extend(self._markdown_entity(entity))
        lines.extend(("### Associations", ""))
        for association in self._associations(model):
            lines.extend(self._markdown_association(model, association))

        if model.inheritances:
            lines.extend(("### Héritages ISA", ""))
            for inheritance in sorted(
                model.inheritances.values(), key=lambda item: item.id
            ):
                parent = model.entities[inheritance.parent_entity_id]
                children = ", ".join(
                    model.entities[item].name for item in inheritance.child_entity_ids
                )
                lines.append(
                    f"- **{parent.name}** → {children} (`{inheritance.strategy.value}`)"
                )
            lines.append("")

        lines.extend(("## Modèle logique", ""))
        if mld is None:
            lines.extend(("*MLD indisponible tant que le MCD reste invalide.*", ""))
        else:
            lines.extend(
                (
                    "### Diagramme",
                    "",
                    "```mermaid",
                    DiagramTextExporter().render_mld_mermaid(mld).rstrip(),
                    "```",
                    "",
                    "### Tables",
                    "",
                )
            )
            for table in self._tables(mld):
                lines.extend(self._markdown_table(mld, table))

        lines.extend(("## Documentation technique", ""))
        for entity in self._entities(model):
            lines.extend(self._markdown_technical_entity(model, entity))
        return "\n".join(lines).rstrip() + "\n"

    def _markdown_entity(self, entity: Entity) -> list[str]:
        lines = [
            f"#### {entity.name}",
            "",
            "Description : *non renseignée dans le MCD.*",
            "",
        ]
        lines.extend(self._markdown_attribute_table(entity.attributes))
        return lines

    def _markdown_association(
        self, model: MCDModel, association: Association
    ) -> list[str]:
        lines = [
            f"#### {association.name}",
            "",
            f"- Historisée : **{'oui' if association.is_historized else 'non'}**",
            f"- Matérialisation : `{association.materialization_strategy.value}`",
            "",
            "| Entité | Cardinalité | Rôle |",
            "|---|---|---|",
        ]
        for relation in sorted(
            model.connected_relations(association.id), key=lambda item: item.id
        ):
            entity = model.entities[relation.entity_id]
            cardinality = relation.cardinality.label if relation.cardinality else "?"
            lines.append(
                f"| {entity.name} | `{cardinality}` | {relation.role or '—'} |"
            )
        lines.append("")
        if association.attributes:
            lines.extend(self._markdown_attribute_table(association.attributes))
        return lines

    @staticmethod
    def _markdown_attribute_table(attributes: list[Attribute]) -> list[str]:
        lines = [
            "| Attribut | Type | ID | Présence | Défaut | Unique | Commentaire |",
            "|---|---|:---:|---|---|:---:|---|",
        ]
        for attribute in attributes:
            type_label = ModelDocumentationGenerator._attribute_type(attribute)
            presence = (
                "automatique"
                if attribute.nullable is None
                else ("facultatif" if attribute.nullable else "obligatoire")
            )
            lines.append(
                f"| {attribute.name} | `{type_label}` | "
                f"{'#' if attribute.identifier else '—'} | {presence} | "
                f"`{attribute.default or '—'}` | "
                f"{'✓' if attribute.unique else '—'} | {attribute.comment or '—'} |"
            )
            for constraint in attribute.constraints:
                lines.append(
                    f"| ↳ contrainte | `CHECK ({constraint})` | — | — | — | — | — |"
                )
        if not attributes:
            lines.append("| *Aucun attribut* | — | — | — | — | — | — |")
        lines.append("")
        return lines

    def _markdown_table(self, model: MLDModel, table: MLDTable) -> list[str]:
        lines = [
            f"#### {table.name}",
            "",
            "| Colonne | Type | Rôles | Nullabilité | Défaut |",
            "|---|---|---|---|---|",
        ]
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
            nullable = (
                "NULL"
                if column.nullable is True
                else "NOT NULL"
                if column.nullable is False
                else "auto"
            )
            lines.append(
                f"| {column.name} | `{column.data_type.label}` | "
                f"{', '.join(roles) or '—'} | {nullable} | "
                f"`{column.default or '—'}` |"
            )
        lines.append("")
        for foreign_key in table.foreign_keys:
            local = ", ".join(
                table.column_by_id(item).name for item in foreign_key.column_ids
            )
            target = model.table_by_id(foreign_key.referenced_table_id)
            distant = ", ".join(
                target.column_by_id(item).name
                for item in foreign_key.referenced_column_ids
            )
            lines.append(f"- FK `{local}` → **{target.name}**(`{distant}`)")
        for unique_constraint in table.unique_constraints:
            names = ", ".join(
                table.column_by_id(item).name for item in unique_constraint.column_ids
            )
            lines.append(f"- UNIQUE (`{names}`)")
        for check_constraint in table.check_constraints:
            lines.append(f"- CHECK (`{check_constraint.expression}`)")
        for index in table.indexes:
            names = ", ".join(
                table.column_by_id(item).name for item in index.column_ids
            )
            lines.append(f"- INDEX **{index.name}** (`{names}`)")
        lines.append("")
        return lines

    def _markdown_technical_entity(self, model: MCDModel, entity: Entity) -> list[str]:
        lines = [
            "```yaml",
            f"{entity.name}:",
            "  description: non renseignée",
            "  attributs:",
        ]
        for attribute in entity.attributes:
            lines.extend(
                (
                    f"    - nom: {attribute.name}",
                    f"      type: {self._attribute_type(attribute)}",
                    f"      identifiant: {'oui' if attribute.identifier else 'non'}",
                )
            )
        if not entity.attributes:
            lines.append("    []")
        lines.append("  relations:")
        relations = sorted(
            (
                relation
                for relation in model.relations.values()
                if relation.entity_id == entity.id
            ),
            key=lambda item: item.id,
        )
        for relation in relations:
            association = model.associations[relation.association_id]
            others = sorted(
                {
                    model.entities[item.entity_id].name
                    for item in model.connected_relations(association.id)
                    if item.id != relation.id
                }
            )
            target = ", ".join(others) or entity.name
            cardinality = relation.cardinality.label if relation.cardinality else "?"
            lines.extend(
                (
                    f"    - association: {association.name}",
                    f"      cible: {target}",
                    f"      cardinalite: {cardinality}",
                )
            )
        if not relations:
            lines.append("    []")
        lines.extend(("```", ""))
        return lines

    def _html(
        self,
        model: MCDModel,
        mld: MLDModel | None,
        title: str,
        warnings: list[str],
        mcd_image: str | None,
        mld_image: str | None,
    ) -> str:
        parts = [
            '<!doctype html><html lang="fr"><head><meta charset="utf-8">',
            f"<title>{html.escape(title)}</title>",
            "<style>body{font-family:Arial,sans-serif;color:#243047;max-width:1100px;"
            "margin:2rem auto;padding:0 1rem}h1,h2,h3{color:#26364f}"
            "table{border-collapse:collapse;width:100%;margin:1rem 0 2rem}"
            "th,td{border:1px solid #ccd4df;padding:.45rem;text-align:left}"
            "th{background:#eaf1f9}.diagram{max-width:100%;height:auto;"
            "border:1px solid #d8dee8}.warning{background:#fff4d6;padding:1rem}"
            "pre{background:#f5f7fa;padding:1rem;white-space:pre-wrap}"
            ".card{page-break-inside:avoid}</style></head><body>",
            f"<h1>{html.escape(title)}</h1>",
            f"<p>Généré par MERISOR {__version__}.</p>",
        ]
        if warnings:
            parts.append(
                '<div class="warning"><strong>Avertissements</strong><ul>'
                + "".join(f"<li>{html.escape(item)}</li>" for item in warnings)
                + "</ul></div>"
            )
        parts.extend(
            ("<h2>Modèle conceptuel</h2>", self._html_mcd_diagram(model, mcd_image))
        )
        parts.append("<h3>Entités</h3>")
        for entity in self._entities(model):
            parts.extend(
                (
                    f'<section class="card"><h4>{html.escape(entity.name)}</h4>',
                    "<p><em>Description non renseignée dans le MCD.</em></p>",
                    self._html_attributes(entity.attributes),
                    "</section>",
                )
            )
        parts.append("<h3>Associations et cardinalités</h3>")
        for association in self._associations(model):
            parts.append(
                f'<section class="card"><h4>{html.escape(association.name)}</h4>'
                f"<p>Historisée : {'oui' if association.is_historized else 'non'} — "
                "Matérialisation : "
                f"{html.escape(association.materialization_strategy.value)}</p><ul>"
            )
            for relation in sorted(
                model.connected_relations(association.id), key=lambda item: item.id
            ):
                cardinality = (
                    relation.cardinality.label if relation.cardinality else "?"
                )
                role = f" — {html.escape(relation.role)}" if relation.role else ""
                parts.append(
                    f"<li>{html.escape(model.entities[relation.entity_id].name)} : "
                    f"{html.escape(cardinality)}{role}</li>"
                )
            parts.append("</ul>")
            if association.attributes:
                parts.append(self._html_attributes(association.attributes))
            parts.append("</section>")

        parts.append("<h2>Modèle logique</h2>")
        if mld is None:
            parts.append(
                "<p><em>MLD indisponible tant que le MCD reste invalide.</em></p>"
            )
        else:
            parts.append(self._html_mld_diagram(mld, mld_image))
            for table in self._tables(mld):
                parts.append(self._html_table(mld, table))

        parts.extend(
            (
                "<h2>Documentation technique</h2>",
                "<p>Les descriptions métier absentes du MCD ne sont jamais inventées.</p>",
            )
        )
        for entity in self._entities(model):
            yaml_text = "\n".join(self._markdown_technical_entity(model, entity)[1:-2])
            parts.append(f"<pre>{html.escape(yaml_text)}</pre>")
        parts.append("</body></html>")
        return "".join(parts)

    @staticmethod
    def _html_mcd_diagram(model: MCDModel, image: str | None) -> str:
        if image:
            return f'<img class="diagram" alt="Diagramme MCD" src="{image}">'
        source = DiagramTextExporter().render_mcd_mermaid(model)
        return f"<pre>{html.escape(source)}</pre>"

    @staticmethod
    def _html_mld_diagram(model: MLDModel, image: str | None) -> str:
        if image:
            return f'<img class="diagram" alt="Diagramme MLD" src="{image}">'
        source = DiagramTextExporter().render_mld_mermaid(model)
        return f"<pre>{html.escape(source)}</pre>"

    def _html_table(self, model: MLDModel, table: MLDTable) -> str:
        rows: list[str] = []
        for column in table.columns:
            roles: list[str] = []
            if table.is_primary_key(column.id):
                roles.append("PK")
            if table.is_foreign_key(column.id):
                roles.append("FK")
            if table.is_unique(column.id):
                roles.append("UNIQUE")
            rows.append(
                f"<tr><td>{html.escape(column.name)}</td>"
                f"<td>{html.escape(column.data_type.label)}</td>"
                f"<td>{html.escape(', '.join(roles) or '—')}</td>"
                f"<td>{self._nullability(column.nullable)}</td></tr>"
            )
        constraints: list[str] = []
        for foreign_key in table.foreign_keys:
            local = ", ".join(
                table.column_by_id(item).name for item in foreign_key.column_ids
            )
            target = model.table_by_id(foreign_key.referenced_table_id)
            distant = ", ".join(
                target.column_by_id(item).name
                for item in foreign_key.referenced_column_ids
            )
            constraints.append(
                f"FK {html.escape(local)} → {html.escape(target.name)}"
                f"({html.escape(distant)})"
            )
        for unique_constraint in table.unique_constraints:
            names = ", ".join(
                table.column_by_id(item).name for item in unique_constraint.column_ids
            )
            constraints.append(f"UNIQUE ({html.escape(names)})")
        for check_constraint in table.check_constraints:
            constraints.append(f"CHECK ({html.escape(check_constraint.expression)})")
        constraint_list = "".join(f"<li>{item}</li>" for item in constraints)
        return (
            f'<section class="card"><h3>{html.escape(table.name)}</h3>'
            "<table><thead><tr><th>Colonne</th><th>Type</th><th>Rôles</th>"
            "<th>Nullabilité</th></tr></thead><tbody>"
            + "".join(rows)
            + "</tbody></table>"
            + (f"<ul>{constraint_list}</ul>" if constraints else "")
            + "</section>"
        )

    @staticmethod
    def _html_attributes(attributes: list[Attribute]) -> str:
        rows = [
            f"<tr><td>{html.escape(attribute.name)}</td>"
            f"<td>{html.escape(ModelDocumentationGenerator._attribute_type(attribute))}</td>"
            f"<td>{'#' if attribute.identifier else '—'}</td>"
            f"<td>{html.escape(attribute.comment or '—')}</td></tr>"
            for attribute in attributes
        ]
        if not rows:
            rows.append('<tr><td colspan="4"><em>Aucun attribut</em></td></tr>')
        return (
            "<table><thead><tr><th>Attribut</th><th>Type</th><th>ID</th>"
            "<th>Commentaire</th></tr></thead><tbody>"
            + "".join(rows)
            + "</tbody></table>"
        )

    @staticmethod
    def _attribute_type(attribute: Attribute) -> str:
        if attribute.data_type is not None:
            return attribute.data_type.label
        return "INTEGER" if attribute.identifier else "VARCHAR(100)"

    @staticmethod
    def _nullability(nullable: bool | None) -> str:
        if nullable is None:
            return "automatique"
        return "NULL" if nullable else "NOT NULL"

    @staticmethod
    def _entities(model: MCDModel) -> list[Entity]:
        return sorted(
            model.entities.values(), key=lambda item: (item.name.casefold(), item.id)
        )

    @staticmethod
    def _associations(model: MCDModel) -> list[Association]:
        return sorted(
            model.associations.values(),
            key=lambda item: (item.name.casefold(), item.id),
        )

    @staticmethod
    def _tables(model: MLDModel) -> list[MLDTable]:
        return sorted(model.tables, key=lambda item: (item.name.casefold(), item.id))
