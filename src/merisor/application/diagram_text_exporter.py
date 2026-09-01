"""Exports documentaires Mermaid et Graphviz indépendants de Qt."""

from __future__ import annotations

import html
import os
import tempfile
from contextlib import suppress
from enum import Enum
from pathlib import Path

from merisor.domain import (
    Association,
    Attribute,
    Entity,
    MCDModel,
    MLDColumn,
    MLDModel,
    MLDTable,
)


class DiagramTextExportError(RuntimeError):
    """Le modèle ne peut pas être écrit dans le format documentaire demandé."""


class DiagramTextFormat(str, Enum):
    MERMAID = "mermaid"
    GRAPHVIZ = "graphviz"

    @classmethod
    def from_path(cls, path: str | Path) -> DiagramTextFormat:
        suffix = Path(path).suffix.casefold()
        if suffix in {".mmd", ".mermaid"}:
            return cls.MERMAID
        if suffix in {".dot", ".gv"}:
            return cls.GRAPHVIZ
        raise DiagramTextExportError(
            "Format textuel non pris en charge. Utilisez Mermaid (.mmd) "
            "ou Graphviz (.dot)."
        )


class DiagramTextExporter:
    """Produit une représentation stable du modèle, et non une capture du canvas."""

    SUPPORTED_SUFFIXES = frozenset({".mmd", ".mermaid", ".dot", ".gv"})

    def export_mcd(self, model: MCDModel, path: str | Path) -> Path:
        if not model.entities and not model.associations:
            raise DiagramTextExportError("Le MCD est vide : aucun objet à exporter.")
        target = Path(path)
        export_format = DiagramTextFormat.from_path(target)
        text = (
            self.render_mcd_mermaid(model)
            if export_format is DiagramTextFormat.MERMAID
            else self.render_mcd_graphviz(model)
        )
        return self._write(target, text)

    def export_mld(self, model: MLDModel, path: str | Path) -> Path:
        if not model.tables:
            raise DiagramTextExportError("Le MLD est vide : aucune table à exporter.")
        target = Path(path)
        export_format = DiagramTextFormat.from_path(target)
        text = (
            self.render_mld_mermaid(model)
            if export_format is DiagramTextFormat.MERMAID
            else self.render_mld_graphviz(model)
        )
        return self._write(target, text)

    @staticmethod
    def _nodes(model: MCDModel) -> list[Entity | Association]:
        nodes: list[Entity | Association] = list(model.entities.values())
        nodes.extend(model.associations.values())
        return sorted(nodes, key=lambda item: (item.name.casefold(), item.id))

    @staticmethod
    def _attribute_line(attribute: Attribute) -> str:
        name = attribute.name
        identifier = attribute.identifier
        data_type = attribute.data_type
        type_label = (
            data_type.label
            if data_type is not None
            else ("INTEGER" if identifier else "VARCHAR(100)")
        )
        return f"{'# ' if identifier else ''}{name} : {type_label}"

    def render_mcd_mermaid(self, model: MCDModel) -> str:
        nodes = self._nodes(model)
        node_ids = {node.id: f"n{index}" for index, node in enumerate(nodes)}
        lines = ["flowchart LR"]
        for node in nodes:
            label_lines = [node.name]
            label_lines.extend(self._attribute_line(item) for item in node.attributes)
            label = "<br/>".join(html.escape(item, quote=True) for item in label_lines)
            syntax = (
                f'{{"{label}"}}' if isinstance(node, Association) else f'["{label}"]'
            )
            lines.append(f"    {node_ids[node.id]}{syntax}")
        for relation in sorted(model.relations.values(), key=lambda item: item.id):
            if (
                relation.entity_id not in node_ids
                or relation.association_id not in node_ids
            ):
                continue
            cardinality = relation.cardinality.label if relation.cardinality else "?"
            edge_label = cardinality
            if relation.role:
                edge_label += f" — {relation.role}"
            lines.append(
                f'    {node_ids[relation.entity_id]} ---|"'
                f'{html.escape(edge_label, quote=True)}"| '
                f"{node_ids[relation.association_id]}"
            )
        for inheritance in sorted(
            model.inheritances.values(), key=lambda item: item.id
        ):
            parent = node_ids.get(inheritance.parent_entity_id)
            if parent is None:
                continue
            for child_id in inheritance.child_entity_ids:
                child = node_ids.get(child_id)
                if child is not None:
                    lines.append(
                        f'    {parent} -->|"ISA {inheritance.strategy.value}"| {child}'
                    )
        return "\n".join(lines) + "\n"

    def render_mcd_graphviz(self, model: MCDModel) -> str:
        nodes = self._nodes(model)
        node_ids = {node.id: f"n{index}" for index, node in enumerate(nodes)}
        lines = [
            "digraph MERISOR_MCD {",
            '    graph [rankdir=LR, bgcolor="white"];',
            '    node [fontname="Sans", color="#2f3b52"];',
            '    edge [fontname="Sans", color="#60748c"];',
        ]
        for node in nodes:
            label_lines = [node.name]
            label_lines.extend(self._attribute_line(item) for item in node.attributes)
            label = self._dot_escape("\n".join(label_lines))
            shape = "diamond" if isinstance(node, Association) else "box"
            lines.append(f'    {node_ids[node.id]} [shape={shape}, label="{label}"];')
        for relation in sorted(model.relations.values(), key=lambda item: item.id):
            entity = node_ids.get(relation.entity_id)
            association = node_ids.get(relation.association_id)
            if entity is None or association is None:
                continue
            label = relation.cardinality.label if relation.cardinality else "?"
            if relation.role:
                label += f" — {relation.role}"
            lines.append(
                f'    {entity} -> {association} [dir=none, label="{self._dot_escape(label)}"];'
            )
        for inheritance in sorted(
            model.inheritances.values(), key=lambda item: item.id
        ):
            parent = node_ids.get(inheritance.parent_entity_id)
            if parent is None:
                continue
            for child_id in inheritance.child_entity_ids:
                child = node_ids.get(child_id)
                if child is not None:
                    lines.append(
                        f'    {parent} -> {child} [label="ISA {inheritance.strategy.value}", arrowhead=empty];'
                    )
        lines.append("}")
        return "\n".join(lines) + "\n"

    @staticmethod
    def _mld_column_line(table: MLDTable, column: MLDColumn) -> str:
        roles: list[str] = []
        if table.is_primary_key(column.id):
            roles.append("PK")
        if table.is_foreign_key(column.id):
            roles.append("FK")
        prefix = f"{'/'.join(roles)} " if roles else ""
        return f"{prefix}{column.name} : {column.data_type.label}"

    def render_mld_mermaid(self, model: MLDModel) -> str:
        tables = sorted(model.tables, key=lambda item: (item.name.casefold(), item.id))
        table_ids = {table.id: f"t{index}" for index, table in enumerate(tables)}
        lines = ["flowchart LR"]
        for table in tables:
            label_lines = [table.name]
            label_lines.extend(
                self._mld_column_line(table, item) for item in table.columns
            )
            label = "<br/>".join(html.escape(item, quote=True) for item in label_lines)
            lines.append(f'    {table_ids[table.id]}["{label}"]')
        for table in tables:
            for foreign_key in table.foreign_keys:
                target = table_ids.get(foreign_key.referenced_table_id)
                if target is None:
                    continue
                names = ", ".join(
                    table.column_by_id(item).name for item in foreign_key.column_ids
                )
                lines.append(
                    f'    {table_ids[table.id]} -->|"FK '
                    f'{html.escape(names, quote=True)}"| {target}'
                )
        return "\n".join(lines) + "\n"

    def render_mld_graphviz(self, model: MLDModel) -> str:
        tables = sorted(model.tables, key=lambda item: (item.name.casefold(), item.id))
        table_ids = {table.id: f"t{index}" for index, table in enumerate(tables)}
        lines = [
            "digraph MERISOR_MLD {",
            '    graph [rankdir=LR, bgcolor="white"];',
            '    node [shape=box, fontname="Sans", color="#2f3b52"];',
            '    edge [fontname="Sans", color="#60748c"];',
        ]
        for table in tables:
            label_lines = [table.name]
            label_lines.extend(
                self._mld_column_line(table, item) for item in table.columns
            )
            label = self._dot_escape("\n".join(label_lines))
            lines.append(f'    {table_ids[table.id]} [label="{label}"];')
        for table in tables:
            for foreign_key in table.foreign_keys:
                target = table_ids.get(foreign_key.referenced_table_id)
                if target is None:
                    continue
                names = ", ".join(
                    table.column_by_id(item).name for item in foreign_key.column_ids
                )
                lines.append(
                    f"    {table_ids[table.id]} -> {target} "
                    f'[label="FK {self._dot_escape(names)}"];'
                )
        lines.append("}")
        return "\n".join(lines) + "\n"

    @staticmethod
    def _dot_escape(value: str) -> str:
        return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")

    @staticmethod
    def _write(target: Path, text: str) -> Path:
        if not target.parent.exists():
            raise DiagramTextExportError(
                f"Le dossier de destination n'existe pas : {target.parent}"
            )
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                prefix=f".{target.stem}-",
                suffix=target.suffix,
                dir=target.parent,
                delete=False,
            ) as temporary:
                temporary.write(text)
                temporary_path = Path(temporary.name)
            os.replace(temporary_path, target)
        except OSError as error:
            raise DiagramTextExportError(
                f"Impossible d'écrire le fichier : {error}"
            ) from error
        finally:
            if temporary_path is not None and temporary_path.exists():
                with suppress(OSError):
                    temporary_path.unlink()
        return target
