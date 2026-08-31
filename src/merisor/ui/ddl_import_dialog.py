"""Aperçu obligatoire avant import d'un DDL reverse-engineeré."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QPlainTextEdit,
    QTabWidget,
    QVBoxLayout,
)

from merisor.application import DDLImportResult, render_mld_text


class DDLImportPreviewDialog(QDialog):
    def __init__(
        self, result: DDLImportResult, source_sql: str, parent=None
    ) -> None:  # type: ignore[no-untyped-def]
        super().__init__(parent)
        self.setWindowTitle("Aperçu de l'import SQL / DDL")
        self.resize(900, 680)
        self.result = result

        layout = QVBoxLayout(self)
        headline = QLabel(
            f"{len(result.mld.tables)} table(s) détectée(s) — "
            f"{len(result.mcd.entities)} entité(s), "
            f"{len(result.mcd.associations)} association(s) reconstruite(s)."
        )
        headline.setWordWrap(True)
        layout.addWidget(headline)

        warning = QLabel(
            "⚠ Le passage SQL → MCD repose sur des heuristiques. Vérifiez les "
            "cardinalités et les tables d'association avant de confirmer."
        )
        warning.setWordWrap(True)
        warning.setStyleSheet("color: #8a5a00; font-weight: bold;")
        layout.addWidget(warning)

        tabs = QTabWidget()
        mld_text = QPlainTextEdit(render_mld_text(result.mld))
        mld_text.setReadOnly(True)
        mcd_text = QPlainTextEdit(self._mcd_summary(result))
        mcd_text.setReadOnly(True)
        source_text = QPlainTextEdit(source_sql)
        source_text.setReadOnly(True)
        tabs.addTab(mld_text, "MLD détecté")
        tabs.addTab(mcd_text, "MCD reconstruit")
        tabs.addTab(source_text, "DDL source")
        layout.addWidget(tabs, 1)

        if result.warnings:
            warnings = QPlainTextEdit(
                "\n".join(f"• {message}" for message in result.warnings)
            )
            warnings.setReadOnly(True)
            warnings.setMaximumHeight(110)
            layout.addWidget(warnings)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText(
            "Importer le MCD et le MLD"
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    @staticmethod
    def _mcd_summary(result: DDLImportResult) -> str:
        lines: list[str] = []
        for entity in result.mcd.entities.values():
            lines.append(entity.name)
            lines.extend(
                f"  {'# ' if attribute.identifier else '- '}{attribute.name}"
                for attribute in entity.attributes
            )
            lines.append("")
        for association in result.mcd.associations.values():
            lines.append(f"◇ {association.name}")
            for relation in result.mcd.connected_relations(association.id):
                entity = result.mcd.entities[relation.entity_id]
                role = f" [{relation.role}]" if relation.role else ""
                lines.append(f"  {entity.name} {relation.cardinality}{role}")
            lines.append("")
        for inheritance in result.mcd.inheritances.values():
            parent = result.mcd.entities[inheritance.parent_entity_id]
            children = ", ".join(
                result.mcd.entities[item].name
                for item in inheritance.child_entity_ids
            )
            lines.append(f"ISA {parent.name} → {children} ({inheritance.strategy.value})")
        return "\n".join(lines).strip() + "\n"
