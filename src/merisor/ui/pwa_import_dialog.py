"""Aperçu vérifiable d'un MCD inféré depuis les sources d'une PWA."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QPlainTextEdit,
    QTabWidget,
    QVBoxLayout,
)

from merisor.application import PwaImportResult


class PwaImportPreviewDialog(QDialog):
    """Présente les inférences et exige une confirmation explicite."""

    def __init__(self, result: PwaImportResult, source_label: str, parent=None) -> None:  # type: ignore[no-untyped-def]
        super().__init__(parent)
        self.setWindowTitle("Aperçu de l'import PWA / IndexedDB")
        self.resize(940, 700)
        self.import_result = result

        layout = QVBoxLayout(self)
        databases = ", ".join(result.database_names) or "nom non détecté"
        headline = QLabel(
            f"{result.scanned_files} fichier(s) analysé(s) — base(s) : {databases} — "
            f"{len(result.mcd.entities)} entité(s), "
            f"{len(result.mcd.associations)} association(s) proposée(s)."
        )
        headline.setWordWrap(True)
        layout.addWidget(headline)

        warning = QLabel(
            "⚠ L'analyse est locale et heuristique. Les sources décrivent le schéma "
            "IndexedDB, mais les enregistrements réellement présents sur un appareil "
            "ne sont pas lus. Vérifiez le MCD avant de confirmer."
        )
        warning.setWordWrap(True)
        warning.setStyleSheet("color: #8a5a00; font-weight: bold;")
        layout.addWidget(warning)

        tabs = QTabWidget(self)
        tabs.addTab(self._read_only(self._mcd_summary(result)), "MCD proposé")
        tabs.addTab(self._read_only(self._evidence_summary(result)), "Preuves")
        tabs.addTab(self._read_only(self._validation_summary(result)), "Validation")
        tabs.addTab(
            self._read_only(
                f"Source : {source_label}\n"
                f"Fichiers analysés : {result.scanned_files}\n"
                f"Bases détectées : {databases}\n\n"
                "Pris en charge : schémas Dexie, createObjectStore/createIndex "
                "IndexedDB natifs et interfaces/types TypeScript associés.\n"
                "Ignorés : node_modules, dist, build, données du navigateur et "
                "logique métier ne déclarant aucun schéma persistant."
            ),
            "Portée de l'analyse",
        )
        layout.addWidget(tabs, 1)

        if result.warnings:
            warnings = self._read_only(
                "\n".join(f"• {message}" for message in result.warnings)
            )
            warnings.setMaximumHeight(100)
            layout.addWidget(warnings)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        import_button = self.buttons.button(QDialogButtonBox.StandardButton.Ok)
        import_button.setText("Importer le MCD proposé")
        import_button.setEnabled(result.validation.is_valid)
        if not result.validation.is_valid:
            import_button.setToolTip(
                "Corrigez les erreurs détectées dans les sources avant l'import."
            )
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

    @staticmethod
    def _read_only(text: str) -> QPlainTextEdit:
        widget = QPlainTextEdit(text)
        widget.setReadOnly(True)
        return widget

    @staticmethod
    def _mcd_summary(result: PwaImportResult) -> str:
        lines: list[str] = []
        for entity in result.mcd.entities.values():
            lines.append(entity.name)
            for attribute in entity.attributes:
                flags = ["#" if attribute.identifier else "-"]
                if attribute.unique:
                    flags.append("UNIQUE")
                if attribute.auto_increment:
                    flags.append("AUTO")
                data_type = f" : {attribute.data_type}" if attribute.data_type else ""
                lines.append(f"  {'/'.join(flags)} {attribute.name}{data_type}")
            lines.append("")
        for association in result.mcd.associations.values():
            lines.append(f"◇ {association.name}")
            for relation in result.mcd.connected_relations(association.id):
                entity = result.mcd.entities[relation.entity_id]
                role = f" [{relation.role}]" if relation.role else ""
                lines.append(f"  {entity.name} {relation.cardinality}{role}")
            lines.append("")
        return "\n".join(lines).strip() + "\n"

    @staticmethod
    def _evidence_summary(result: PwaImportResult) -> str:
        return (
            "\n".join(
                f"[{item.confidence.display_name}] {item.path}:{item.line} — {item.message}"
                for item in result.evidence
            )
            or "Aucune preuve détaillée."
        )

    @staticmethod
    def _validation_summary(result: PwaImportResult) -> str:
        if not result.validation.issues:
            return "✓ Le MCD proposé est structurellement valide."
        return "\n".join(
            f"{'ERREUR' if issue in result.validation.errors else 'AVERTISSEMENT'} "
            f"[{issue.code}] — {issue.message}"
            for issue in result.validation.issues
        )
