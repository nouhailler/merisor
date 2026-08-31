"""Génération SQL multi-dialecte exclusivement à partir du modèle MLD."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from merisor import __version__
from merisor.domain import (
    MLDColumn,
    MLDDataType,
    MLDDataTypeName,
    MLDForeignKey,
    MLDIndex,
    MLDModel,
    MLDReferentialAction,
    MLDTable,
)


class SQLTarget(str, Enum):
    POSTGRESQL = "postgresql"
    SQLITE = "sqlite"
    MYSQL = "mysql"

    @property
    def display_name(self) -> str:
        return {
            SQLTarget.POSTGRESQL: "PostgreSQL",
            SQLTarget.SQLITE: "SQLite",
            SQLTarget.MYSQL: "MariaDB / MySQL",
        }[self]


class SQLValidationSeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True, slots=True)
class SQLValidationIssue:
    severity: SQLValidationSeverity
    code: str
    message: str
    table_id: str | None = None


@dataclass(frozen=True, slots=True)
class SQLValidationReport:
    issues: tuple[SQLValidationIssue, ...]

    @property
    def errors(self) -> tuple[SQLValidationIssue, ...]:
        return tuple(
            issue
            for issue in self.issues
            if issue.severity is SQLValidationSeverity.ERROR
        )

    @property
    def warnings(self) -> tuple[SQLValidationIssue, ...]:
        return tuple(
            issue
            for issue in self.issues
            if issue.severity is SQLValidationSeverity.WARNING
        )

    @property
    def is_valid(self) -> bool:
        return not self.errors


class SQLGenerationError(ValueError):
    def __init__(self, report: SQLValidationReport) -> None:
        self.report = report
        super().__init__(
            "Impossible de générer le SQL : "
            f"{len(report.errors)} erreur(s) dans le MLD."
        )


@dataclass(frozen=True, slots=True)
class SQLGenerationOptions:
    create_tables: bool = True
    create_primary_keys: bool = True
    create_foreign_keys: bool = True
    create_unique_constraints: bool = True
    create_checks: bool = True
    create_indexes: bool = True


class SQLDialect(ABC):
    """Stratégie regroupant toutes les différences syntaxiques d'un SGBD."""

    target: SQLTarget
    quote_character = '"'
    supports_alter_add_foreign_key = True
    reserved_words = frozenset(
        {
            "check",
            "constraint",
            "foreign",
            "group",
            "index",
            "key",
            "order",
            "primary",
            "references",
            "select",
            "table",
            "unique",
            "user",
            "where",
        }
    )

    def quote_identifier(self, name: str) -> str:
        quote = self.quote_character
        escaped = name.replace(quote, quote * 2)
        return f"{quote}{escaped}{quote}"

    @abstractmethod
    def render_type(self, data_type: MLDDataType) -> str:
        raise NotImplementedError

    def render_column(
        self,
        column: MLDColumn,
        *,
        inline_auto_primary_key: bool,
    ) -> str:
        parts = [self.quote_identifier(column.name), self.render_type(column.data_type)]
        if column.auto_increment:
            before_null = self.identity_before_null(column, inline_auto_primary_key)
            if before_null:
                parts.append(before_null)
        if column.nullable is False and not inline_auto_primary_key:
            parts.append("NOT NULL")
        if column.default is not None:
            parts.extend(("DEFAULT", column.default))
        if column.auto_increment:
            after_null = self.identity_after_null(column, inline_auto_primary_key)
            if after_null:
                parts.append(after_null)
        return " ".join(parts)

    def identity_before_null(
        self, column: MLDColumn, inline_auto_primary_key: bool
    ) -> str:
        del column, inline_auto_primary_key
        return ""

    def identity_after_null(
        self, column: MLDColumn, inline_auto_primary_key: bool
    ) -> str:
        del column, inline_auto_primary_key
        return ""

    def uses_inline_auto_primary_key(self, table: MLDTable) -> bool:
        del table
        return False

    def preamble(self) -> tuple[str, ...]:
        return ()

    def render_column_comment(self, table: MLDTable, column: MLDColumn) -> str:
        if not column.comment:
            return ""
        comment = " ".join(column.comment.splitlines())
        return f"-- Commentaire {table.name}.{column.name} : {comment}"


class PostgreSQLDialect(SQLDialect):
    target = SQLTarget.POSTGRESQL

    def render_type(self, data_type: MLDDataType) -> str:
        mapping = {
            MLDDataTypeName.INTEGER: "INTEGER",
            MLDDataTypeName.BIGINT: "BIGINT",
            MLDDataTypeName.FLOAT: "DOUBLE PRECISION",
            MLDDataTypeName.BOOLEAN: "BOOLEAN",
            MLDDataTypeName.TEXT: "TEXT",
            MLDDataTypeName.DATE: "DATE",
            MLDDataTypeName.TIME: "TIME",
            MLDDataTypeName.DATETIME: "TIMESTAMP",
            MLDDataTypeName.TIMESTAMP: "TIMESTAMP",
        }
        if data_type.name is MLDDataTypeName.VARCHAR:
            return f"VARCHAR({data_type.length})"
        if data_type.name is MLDDataTypeName.DECIMAL:
            return _decimal_type(data_type, "DECIMAL")
        return mapping[data_type.name]

    def identity_before_null(
        self, column: MLDColumn, inline_auto_primary_key: bool
    ) -> str:
        del column, inline_auto_primary_key
        return "GENERATED BY DEFAULT AS IDENTITY"

    def render_column_comment(self, table: MLDTable, column: MLDColumn) -> str:
        if not column.comment:
            return ""
        escaped = column.comment.replace("'", "''")
        return (
            f"COMMENT ON COLUMN {self.quote_identifier(table.name)}."
            f"{self.quote_identifier(column.name)} IS '{escaped}';"
        )


class SQLiteDialect(SQLDialect):
    target = SQLTarget.SQLITE
    supports_alter_add_foreign_key = False

    def render_type(self, data_type: MLDDataType) -> str:
        mapping = {
            MLDDataTypeName.INTEGER: "INTEGER",
            MLDDataTypeName.BIGINT: "INTEGER",
            MLDDataTypeName.DECIMAL: "NUMERIC",
            MLDDataTypeName.FLOAT: "REAL",
            MLDDataTypeName.BOOLEAN: "INTEGER",
            MLDDataTypeName.VARCHAR: "TEXT",
            MLDDataTypeName.TEXT: "TEXT",
            MLDDataTypeName.DATE: "TEXT",
            MLDDataTypeName.TIME: "TEXT",
            MLDDataTypeName.DATETIME: "TEXT",
            MLDDataTypeName.TIMESTAMP: "TEXT",
        }
        return mapping[data_type.name]

    def uses_inline_auto_primary_key(self, table: MLDTable) -> bool:
        return (
            len(table.primary_key) == 1
            and table.column_by_id(table.primary_key[0]).auto_increment
        )

    def identity_after_null(
        self, column: MLDColumn, inline_auto_primary_key: bool
    ) -> str:
        del column
        return "PRIMARY KEY AUTOINCREMENT" if inline_auto_primary_key else ""

    def preamble(self) -> tuple[str, ...]:
        return ("PRAGMA foreign_keys = ON;",)


class MySQLDialect(SQLDialect):
    target = SQLTarget.MYSQL
    quote_character = "`"

    def render_type(self, data_type: MLDDataType) -> str:
        mapping = {
            MLDDataTypeName.INTEGER: "INT",
            MLDDataTypeName.BIGINT: "BIGINT",
            MLDDataTypeName.FLOAT: "DOUBLE",
            MLDDataTypeName.BOOLEAN: "BOOLEAN",
            MLDDataTypeName.TEXT: "TEXT",
            MLDDataTypeName.DATE: "DATE",
            MLDDataTypeName.TIME: "TIME",
            MLDDataTypeName.DATETIME: "DATETIME",
            MLDDataTypeName.TIMESTAMP: "TIMESTAMP",
        }
        if data_type.name is MLDDataTypeName.VARCHAR:
            return f"VARCHAR({data_type.length})"
        if data_type.name is MLDDataTypeName.DECIMAL:
            return _decimal_type(data_type, "DECIMAL")
        return mapping[data_type.name]

    def identity_after_null(
        self, column: MLDColumn, inline_auto_primary_key: bool
    ) -> str:
        del column, inline_auto_primary_key
        return "AUTO_INCREMENT"

    def render_column(
        self,
        column: MLDColumn,
        *,
        inline_auto_primary_key: bool,
    ) -> str:
        rendered = super().render_column(
            column, inline_auto_primary_key=inline_auto_primary_key
        )
        if not column.comment:
            return rendered
        escaped = column.comment.replace("'", "''")
        return f"{rendered} COMMENT '{escaped}'"

    def render_column_comment(self, table: MLDTable, column: MLDColumn) -> str:
        del table, column
        return ""


def _decimal_type(data_type: MLDDataType, name: str) -> str:
    if data_type.precision is None:
        return name
    if data_type.scale is None:
        return f"{name}({data_type.precision})"
    return f"{name}({data_type.precision},{data_type.scale})"


_DIALECTS: dict[SQLTarget, SQLDialect] = {
    SQLTarget.POSTGRESQL: PostgreSQLDialect(),
    SQLTarget.SQLITE: SQLiteDialect(),
    SQLTarget.MYSQL: MySQLDialect(),
}


def sql_dialect(target: SQLTarget | str) -> SQLDialect:
    try:
        normalized = SQLTarget(target)
    except (TypeError, ValueError) as error:
        raise ValueError(f"SGBD cible inconnu : {target!r}.") from error
    return _DIALECTS[normalized]


class MLDSQLValidator:
    """Validation défensive du MLD avant toute production de texte SQL."""

    def validate(self, model: MLDModel, target: SQLTarget | str) -> SQLValidationReport:
        dialect = sql_dialect(target)
        issues: list[SQLValidationIssue] = []
        if not model.tables:
            issues.append(
                self._error("mld.tables_missing", "Le MLD ne contient aucune table.")
            )
            return SQLValidationReport(tuple(issues))

        tables_by_id = {table.id: table for table in model.tables}
        seen_table_names: set[str] = set()
        for table in model.tables:
            table_label = table.name or table.id
            if not isinstance(table.name, str) or not table.name.strip():
                issues.append(
                    self._error(
                        "table.name_missing",
                        "Une table du MLD ne possède pas de nom.",
                        table.id,
                    )
                )
            elif table.name.casefold() in seen_table_names:
                issues.append(
                    self._error(
                        "table.name_duplicate",
                        f'Le nom de table "{table.name}" est dupliqué.',
                        table.id,
                    )
                )
            else:
                seen_table_names.add(table.name.casefold())
            if self._is_reserved(table.name, dialect):
                issues.append(self._reserved_warning("table", table.name, table.id))
            if not table.primary_key:
                issues.append(
                    self._error(
                        "table.primary_key_missing",
                        f"La table {table_label} ne possède pas de clé primaire.",
                        table.id,
                    )
                )

            columns_by_id = {column.id: column for column in table.columns}
            seen_column_names: set[str] = set()
            for column in table.columns:
                if not isinstance(column.name, str) or not column.name.strip():
                    issues.append(
                        self._error(
                            "column.name_missing",
                            f"La table {table_label} contient une colonne sans nom.",
                            table.id,
                        )
                    )
                elif column.name.casefold() in seen_column_names:
                    issues.append(
                        self._error(
                            "column.name_duplicate",
                            f'La table {table_label} duplique la colonne "{column.name}".',
                            table.id,
                        )
                    )
                else:
                    seen_column_names.add(column.name.casefold())
                if not isinstance(column.data_type, MLDDataType):
                    issues.append(
                        self._error(
                            "column.type_unknown",
                            f"Le type de {table_label}.{column.name} est inconnu.",
                            table.id,
                        )
                    )
                if self._is_reserved(column.name, dialect):
                    issues.append(
                        self._reserved_warning("colonne", column.name, table.id)
                    )
                self._validate_auto_increment(table, column, issues)

            missing_pk = set(table.primary_key) - set(columns_by_id)
            if missing_pk:
                issues.append(
                    self._error(
                        "primary_key.column_missing",
                        f"La PK de {table_label} référence une colonne absente.",
                        table.id,
                    )
                )
            for foreign_key in table.foreign_keys:
                self._validate_foreign_key(
                    table, foreign_key, tables_by_id, columns_by_id, issues
                )
            for constraint in table.unique_constraints:
                if not set(constraint.column_ids).issubset(columns_by_id):
                    issues.append(
                        self._error(
                            "unique.column_missing",
                            f"Une contrainte UNIQUE de {table_label} référence "
                            "une colonne absente.",
                            table.id,
                        )
                    )
            for check in table.check_constraints:
                if not check.expression.strip():
                    issues.append(
                        self._error(
                            "check.expression_missing",
                            f"Un CHECK de {table_label} ne contient aucune expression.",
                            table.id,
                        )
                    )
            for index in table.indexes:
                if not set(index.column_ids).issubset(columns_by_id):
                    issues.append(
                        self._error(
                            "index.column_missing",
                            f"L'index {index.name} de {table_label} référence "
                            "une colonne absente.",
                            table.id,
                        )
                    )
                if self._is_reserved(index.name, dialect):
                    issues.append(self._reserved_warning("index", index.name, table.id))
        return SQLValidationReport(tuple(issues))

    def _validate_auto_increment(
        self,
        table: MLDTable,
        column: MLDColumn,
        issues: list[SQLValidationIssue],
    ) -> None:
        if not column.auto_increment:
            return
        if not isinstance(
            column.data_type, MLDDataType
        ) or column.data_type.name not in {
            MLDDataTypeName.INTEGER,
            MLDDataTypeName.BIGINT,
        }:
            issues.append(
                self._error(
                    "column.auto_increment_type",
                    f"La colonne auto-incrémentée {table.name}.{column.name} doit "
                    "être INTEGER ou BIGINT.",
                    table.id,
                )
            )
        if table.primary_key != (column.id,):
            issues.append(
                self._error(
                    "column.auto_increment_primary_key",
                    f"La colonne auto-incrémentée {table.name}.{column.name} doit "
                    "être l'unique colonne de la clé primaire.",
                    table.id,
                )
            )

    def _validate_foreign_key(
        self,
        table: MLDTable,
        foreign_key: MLDForeignKey,
        tables_by_id: dict[str, MLDTable],
        columns_by_id: dict[str, MLDColumn],
        issues: list[SQLValidationIssue],
    ) -> None:
        if not set(foreign_key.column_ids).issubset(columns_by_id):
            issues.append(
                self._error(
                    "foreign_key.local_column_missing",
                    f"Une FK de {table.name} référence une colonne locale absente.",
                    table.id,
                )
            )
            return
        target = tables_by_id.get(foreign_key.referenced_table_id)
        if target is None:
            issues.append(
                self._error(
                    "foreign_key.table_missing",
                    f"La table {table.name} possède une FK vers une table inexistante.",
                    table.id,
                )
            )
            return
        target_columns = {column.id: column for column in target.columns}
        if not set(foreign_key.referenced_column_ids).issubset(target_columns):
            issues.append(
                self._error(
                    "foreign_key.referenced_column_missing",
                    f"La table {table.name} référence {target.name}, mais une "
                    "colonne distante n'existe pas.",
                    table.id,
                )
            )
            return
        candidate_keys = {target.primary_key}
        candidate_keys.update(
            constraint.column_ids for constraint in target.unique_constraints
        )
        if foreign_key.referenced_column_ids not in candidate_keys:
            issues.append(
                self._error(
                    "foreign_key.target_not_unique",
                    f"La FK de {table.name} ne référence ni la PK ni une contrainte "
                    f"UNIQUE complète de {target.name}.",
                    table.id,
                )
            )
        for local_id, target_id in zip(
            foreign_key.column_ids, foreign_key.referenced_column_ids, strict=True
        ):
            local_type = columns_by_id[local_id].data_type
            target_type = target_columns[target_id].data_type
            if local_type != target_type:
                issues.append(
                    self._error(
                        "foreign_key.type_mismatch",
                        f"Les types de la FK {table.name}.{columns_by_id[local_id].name} "
                        f"et de {target.name}.{target_columns[target_id].name} diffèrent.",
                        table.id,
                    )
                )
        if foreign_key.on_delete is MLDReferentialAction.SET_NULL and any(
            columns_by_id[column_id].nullable is False
            for column_id in foreign_key.column_ids
        ):
            issues.append(
                self._error(
                    "foreign_key.set_null_not_nullable",
                    f"La FK de {table.name} utilise ON DELETE SET NULL sur une "
                    "colonne NOT NULL.",
                    table.id,
                )
            )

    @staticmethod
    def _is_reserved(name: object, dialect: SQLDialect) -> bool:
        return isinstance(name, str) and name.casefold() in dialect.reserved_words

    @staticmethod
    def _error(
        code: str, message: str, table_id: str | None = None
    ) -> SQLValidationIssue:
        return SQLValidationIssue(SQLValidationSeverity.ERROR, code, message, table_id)

    @staticmethod
    def _reserved_warning(
        kind: str, name: str, table_id: str | None
    ) -> SQLValidationIssue:
        return SQLValidationIssue(
            SQLValidationSeverity.WARNING,
            "identifier.reserved_word",
            f'Le nom de {kind} "{name}" est réservé ; il sera échappé.',
            table_id,
        )


class SQLGenerator:
    """Orchestrateur commun : validation, dépendances, rendu et contrôle final."""

    def __init__(self, validator: MLDSQLValidator | None = None) -> None:
        self.validator = validator or MLDSQLValidator()

    def validate(self, model: MLDModel, target: SQLTarget | str) -> SQLValidationReport:
        return self.validator.validate(model, target)

    def generate(
        self,
        model: MLDModel,
        target: SQLTarget | str,
        *,
        project_name: str = "Sans titre",
        generated_at: datetime | None = None,
        options: SQLGenerationOptions | None = None,
    ) -> str:
        dialect = sql_dialect(target)
        report = self.validate(model, dialect.target)
        if report.errors:
            raise SQLGenerationError(report)
        active_options = options or SQLGenerationOptions()
        cyclic_keys = self._cyclic_foreign_keys(model)
        deferred_keys = cyclic_keys if dialect.supports_alter_add_foreign_key else set()
        ordered_tables = self._ordered_tables(model, cyclic_keys)
        timestamp = generated_at or datetime.now().astimezone()
        safe_project = " ".join(project_name.splitlines()).strip() or "Sans titre"
        sections = [
            "\n".join(
                (
                    "-- ==================================================",
                    f"-- Généré par MERISOR {__version__}",
                    f"-- Projet : {safe_project}",
                    f"-- Cible : {dialect.target.display_name}",
                    f"-- Date : {timestamp.isoformat(timespec='seconds')}",
                    "-- ==================================================",
                )
            )
        ]
        sections.extend(dialect.preamble())
        if active_options.create_tables:
            sections.extend(
                self._create_table_sql(
                    model,
                    table,
                    dialect,
                    deferred_keys,
                    active_options,
                )
                for table in ordered_tables
            )
        if active_options.create_foreign_keys:
            sections.extend(
                self._alter_foreign_key_sql(model, table, foreign_key, dialect)
                for table in ordered_tables
                for foreign_key in table.foreign_keys
                if (table.id, foreign_key.id) in deferred_keys
            )
        if active_options.create_indexes:
            sections.extend(
                self._index_sql(table, index, dialect)
                for table in ordered_tables
                for index in table.indexes
            )
        script = "\n\n".join(section for section in sections if section) + "\n"
        self._validate_generated_script(
            script,
            expected_tables=len(model.tables) if active_options.create_tables else 0,
        )
        return script

    def _create_table_sql(
        self,
        model: MLDModel,
        table: MLDTable,
        dialect: SQLDialect,
        deferred_keys: set[tuple[str, str]],
        options: SQLGenerationOptions,
    ) -> str:
        inline_auto_pk = dialect.uses_inline_auto_primary_key(table)
        definitions = [
            dialect.render_column(
                column,
                inline_auto_primary_key=(
                    inline_auto_pk and table.primary_key == (column.id,)
                ),
            )
            for column in table.columns
        ]
        if options.create_primary_keys and table.primary_key and not inline_auto_pk:
            definitions.append(
                "PRIMARY KEY ("
                + self._column_names(table, table.primary_key, dialect)
                + ")"
            )
        if options.create_unique_constraints:
            for constraint in table.unique_constraints:
                name = constraint.name or self._constraint_name(
                    "uq", table, constraint.column_ids
                )
                definitions.append(
                    f"CONSTRAINT {dialect.quote_identifier(name)} UNIQUE ("
                    + self._column_names(table, constraint.column_ids, dialect)
                    + ")"
                )
        if options.create_checks:
            for check in table.check_constraints:
                name = check.name or self._safe_name(f"ck_{table.name}_{check.id}")
                definitions.append(
                    f"CONSTRAINT {dialect.quote_identifier(name)} "
                    f"CHECK ({check.expression})"
                )
        if options.create_foreign_keys:
            for foreign_key in table.foreign_keys:
                if (table.id, foreign_key.id) not in deferred_keys:
                    definitions.append(
                        self._foreign_key_clause(model, table, foreign_key, dialect)
                    )
        body = ",\n".join(f"    {definition}" for definition in definitions)
        create_statement = (
            f"-- Table : {table.name}\n"
            f"CREATE TABLE {dialect.quote_identifier(table.name)} (\n"
            f"{body}\n"
            ");"
        )
        comments = [
            dialect.render_column_comment(table, column)
            for column in table.columns
            if column.comment
        ]
        return "\n".join((create_statement, *(item for item in comments if item)))

    def _foreign_key_clause(
        self,
        model: MLDModel,
        table: MLDTable,
        foreign_key: MLDForeignKey,
        dialect: SQLDialect,
    ) -> str:
        target = model.table_by_id(foreign_key.referenced_table_id)
        name = foreign_key.name or self._constraint_name(
            "fk", table, foreign_key.column_ids
        )
        clause = (
            f"CONSTRAINT {dialect.quote_identifier(name)} FOREIGN KEY ("
            f"{self._column_names(table, foreign_key.column_ids, dialect)}) "
            f"REFERENCES {dialect.quote_identifier(target.name)} ("
            f"{self._column_names(target, foreign_key.referenced_column_ids, dialect)})"
        )
        if foreign_key.on_delete is not None:
            clause += f" ON DELETE {foreign_key.on_delete.value}"
        if foreign_key.on_update is not None:
            clause += f" ON UPDATE {foreign_key.on_update.value}"
        return clause

    def _alter_foreign_key_sql(
        self,
        model: MLDModel,
        table: MLDTable,
        foreign_key: MLDForeignKey,
        dialect: SQLDialect,
    ) -> str:
        clause = self._foreign_key_clause(model, table, foreign_key, dialect)
        return f"ALTER TABLE {dialect.quote_identifier(table.name)}\n    ADD {clause};"

    def _index_sql(self, table: MLDTable, index: MLDIndex, dialect: SQLDialect) -> str:
        unique = "UNIQUE " if index.unique else ""
        return (
            f"CREATE {unique}INDEX {dialect.quote_identifier(index.name)}\n"
            f"    ON {dialect.quote_identifier(table.name)} "
            f"({self._column_names(table, index.column_ids, dialect)});"
        )

    @staticmethod
    def _column_names(
        table: MLDTable,
        column_ids: tuple[str, ...],
        dialect: SQLDialect,
    ) -> str:
        return ", ".join(
            dialect.quote_identifier(table.column_by_id(column_id).name)
            for column_id in column_ids
        )

    def _constraint_name(
        self, prefix: str, table: MLDTable, column_ids: tuple[str, ...]
    ) -> str:
        column_names = "_".join(
            table.column_by_id(column_id).name for column_id in column_ids
        )
        return self._safe_name(f"{prefix}_{table.name}_{column_names}")

    @staticmethod
    def _safe_name(value: str) -> str:
        normalized = re.sub(r"[^0-9A-Za-z_]+", "_", value).strip("_")
        return normalized or "constraint"

    def _cyclic_foreign_keys(self, model: MLDModel) -> set[tuple[str, str]]:
        adjacency: dict[str, set[str]] = {table.id: set() for table in model.tables}
        for table in model.tables:
            adjacency[table.id].update(
                foreign_key.referenced_table_id for foreign_key in table.foreign_keys
            )
        components = self._strongly_connected_components(adjacency)
        component_by_table = {
            table_id: component for component in components for table_id in component
        }
        cyclic: set[tuple[str, str]] = set()
        for table in model.tables:
            for foreign_key in table.foreign_keys:
                component = component_by_table[table.id]
                if len(component) > 1 and foreign_key.referenced_table_id in component:
                    cyclic.add((table.id, foreign_key.id))
        return cyclic

    def _ordered_tables(
        self, model: MLDModel, ignored_keys: set[tuple[str, str]]
    ) -> list[MLDTable]:
        tables = {table.id: table for table in model.tables}
        dependencies: dict[str, set[str]] = {table.id: set() for table in model.tables}
        for table in model.tables:
            dependencies[table.id].update(
                foreign_key.referenced_table_id
                for foreign_key in table.foreign_keys
                if (table.id, foreign_key.id) not in ignored_keys
                and foreign_key.referenced_table_id != table.id
            )
        result: list[MLDTable] = []
        remaining = set(tables)
        while remaining:
            ready = sorted(
                (
                    table_id
                    for table_id in remaining
                    if not (dependencies[table_id] & remaining)
                ),
                key=lambda table_id: (
                    tables[table_id].name.casefold(),
                    tables[table_id].id,
                ),
            )
            if not ready:
                ready = sorted(
                    remaining,
                    key=lambda table_id: (
                        tables[table_id].name.casefold(),
                        tables[table_id].id,
                    ),
                )
            for table_id in ready:
                result.append(tables[table_id])
                remaining.remove(table_id)
        return result

    @staticmethod
    def _strongly_connected_components(
        adjacency: dict[str, set[str]],
    ) -> list[set[str]]:
        index = 0
        indexes: dict[str, int] = {}
        lowlinks: dict[str, int] = {}
        stack: list[str] = []
        on_stack: set[str] = set()
        components: list[set[str]] = []

        def visit(node: str) -> None:
            nonlocal index
            indexes[node] = index
            lowlinks[node] = index
            index += 1
            stack.append(node)
            on_stack.add(node)
            for target in sorted(adjacency[node]):
                if target not in adjacency:
                    continue
                if target not in indexes:
                    visit(target)
                    lowlinks[node] = min(lowlinks[node], lowlinks[target])
                elif target in on_stack:
                    lowlinks[node] = min(lowlinks[node], indexes[target])
            if lowlinks[node] == indexes[node]:
                component: set[str] = set()
                while True:
                    member = stack.pop()
                    on_stack.remove(member)
                    component.add(member)
                    if member == node:
                        break
                components.append(component)

        for node in sorted(adjacency):
            if node not in indexes:
                visit(node)
        return components

    @staticmethod
    def _validate_generated_script(script: str, *, expected_tables: int) -> None:
        depth = 0
        quote: str | None = None
        in_comment = False
        index = 0
        while index < len(script):
            character = script[index]
            following = script[index + 1] if index + 1 < len(script) else ""
            if in_comment:
                if character == "\n":
                    in_comment = False
                index += 1
                continue
            if quote is not None:
                if character == quote:
                    if following == quote:
                        index += 2
                        continue
                    quote = None
                index += 1
                continue
            if character == "-" and following == "-":
                in_comment = True
                index += 2
                continue
            if character in {"'", '"', "`"}:
                quote = character
                index += 1
                continue
            if character == "(":
                depth += 1
            elif character == ")":
                depth -= 1
                if depth < 0:
                    raise RuntimeError(
                        "Le SQL généré contient une parenthèse fermante isolée."
                    )
            index += 1
        if quote is not None:
            raise RuntimeError(
                "Le SQL généré contient une chaîne ou un identifiant non fermé."
            )
        if depth:
            raise RuntimeError(
                "Le SQL généré contient des parenthèses non équilibrées."
            )
        if expected_tables and script.count("CREATE TABLE ") != expected_tables:
            raise RuntimeError(
                "Le SQL généré ne contient pas toutes les tables attendues."
            )
        if ";;" in script:
            raise RuntimeError("Le SQL généré contient une instruction vide.")
