"""Génération déterministe de données synthétiques exclusivement depuis le MLD."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import TypeAlias

from merisor.application.sql_generator import (
    MLDSQLValidator,
    SQLDialect,
    SQLTarget,
    SQLValidationSeverity,
    sql_dialect,
)
from merisor.domain import MLDColumn, MLDDataTypeName, MLDForeignKey, MLDModel, MLDTable

TestValue: TypeAlias = (
    int | float | Decimal | bool | str | date | time | datetime | None
)


@dataclass(frozen=True, slots=True)
class TestDataIssue:
    message: str
    table_id: str | None = None


@dataclass(frozen=True, slots=True)
class TestDataGenerationResult:
    script: str
    warnings: tuple[TestDataIssue, ...]
    generated_rows: dict[str, int]


class TestDataGenerationError(ValueError):
    def __init__(self, problems: tuple[TestDataIssue, ...]) -> None:
        self.problems = problems
        super().__init__(
            f"Impossible de générer les données de test : {len(problems)} problème(s)."
        )


class TestDataGenerator:
    """Produit des INSERT portables, ordonnés selon les dépendances FK."""

    DEFAULT_ROWS = 10
    MAX_ROWS_PER_TABLE = 100_000

    def generate(
        self,
        model: MLDModel,
        target: SQLTarget | str,
        row_counts: dict[str, int] | None = None,
        *,
        project_name: str = "Projet MERISOR",
    ) -> TestDataGenerationResult:
        normalized_target = SQLTarget(target)
        dialect = sql_dialect(normalized_target)
        counts = self._normalize_counts(model, row_counts)
        problems = self._validate(model, normalized_target, counts)
        if problems:
            raise TestDataGenerationError(tuple(problems))

        order, nullable_cycle_foreign_keys = self._dependency_order(model, counts)
        empty_target_foreign_keys = {
            foreign_key.id
            for table in model.tables
            if counts[table.id] > 0
            for foreign_key in table.foreign_keys
            if counts[foreign_key.referenced_table_id] == 0
        }
        nulled_foreign_keys = nullable_cycle_foreign_keys | empty_target_foreign_keys
        rows_by_table: dict[str, list[dict[str, TestValue]]] = {}
        warnings = self._warnings(
            model, nullable_cycle_foreign_keys, empty_target_foreign_keys
        )
        statements: list[str] = []
        for table in order:
            rows = self._generate_table_rows(
                table,
                counts[table.id],
                model,
                rows_by_table,
                nulled_foreign_keys,
            )
            uniqueness_problem = self._generated_uniqueness_problem(table, rows)
            if uniqueness_problem is not None:
                raise TestDataGenerationError((uniqueness_problem,))
            rows_by_table[table.id] = rows
            if rows:
                statements.append(self._render_insert(table, rows, dialect))

        header = [
            "-- ==================================================",
            "-- Données de test générées par MERISOR",
            f"-- Projet : {project_name}",
            f"-- Cible : {normalized_target.display_name}",
            "-- Génération uniquement : ce script n'a pas été exécuté.",
            "-- ==================================================",
            "",
        ]
        if warnings:
            header.extend(
                [f"-- AVERTISSEMENT : {warning.message}" for warning in warnings]
            )
            header.append("")
        script = "\n".join((*header, *statements)).rstrip() + "\n"
        return TestDataGenerationResult(script, tuple(warnings), counts)

    def _normalize_counts(
        self, model: MLDModel, requested: dict[str, int] | None
    ) -> dict[str, int]:
        requested = requested or {}
        return {
            table.id: requested.get(table.id, self.DEFAULT_ROWS)
            for table in model.tables
        }

    def _validate(
        self,
        model: MLDModel,
        target: SQLTarget,
        counts: dict[str, int],
    ) -> list[TestDataIssue]:
        problems = [
            TestDataIssue(issue.message, issue.table_id)
            for issue in MLDSQLValidator().validate(model, target).issues
            if issue.severity is SQLValidationSeverity.ERROR
        ]
        for table in model.tables:
            count = counts[table.id]
            if not isinstance(count, int) or isinstance(count, bool) or count < 0:
                problems.append(
                    TestDataIssue(
                        f"La quantité demandée pour {table.name} doit être positive ou nulle.",
                        table.id,
                    )
                )
                continue
            elif count > self.MAX_ROWS_PER_TABLE:
                problems.append(
                    TestDataIssue(
                        f"La quantité demandée pour {table.name} dépasse la limite "
                        f"de {self.MAX_ROWS_PER_TABLE} lignes.",
                        table.id,
                    )
                )
            if count <= 0:
                continue
            for foreign_key in table.foreign_keys:
                if counts[foreign_key.referenced_table_id] == 0:
                    local_columns = [
                        table.column_by_id(item) for item in foreign_key.column_ids
                    ]
                    if any(column.nullable is False for column in local_columns):
                        target_table = model.table_by_id(
                            foreign_key.referenced_table_id
                        )
                        problems.append(
                            TestDataIssue(
                                f"{table.name} exige une référence vers {target_table.name}, "
                                "mais aucune ligne cible n'est demandée.",
                                table.id,
                            )
                        )
        if not problems:
            try:
                self._dependency_order(model, counts)
            except TestDataGenerationError as error:
                problems.extend(error.problems)
        return problems

    def _dependency_order(
        self, model: MLDModel, counts: dict[str, int]
    ) -> tuple[list[MLDTable], set[str]]:
        active = {table.id for table in model.tables if counts[table.id] > 0}
        dependencies: dict[str, set[str]] = {table_id: set() for table_id in active}
        edges: dict[tuple[str, str], list[MLDForeignKey]] = {}
        for table in model.tables:
            if table.id not in active:
                continue
            for foreign_key in table.foreign_keys:
                target_id = foreign_key.referenced_table_id
                if target_id not in active or target_id == table.id:
                    continue
                dependencies[table.id].add(target_id)
                edges.setdefault((table.id, target_id), []).append(foreign_key)

        nullable_cycle_foreign_keys: set[str] = set()
        ordered_ids: list[str] = []
        remaining = set(active)
        while remaining:
            ready = sorted(
                (
                    table_id
                    for table_id in remaining
                    if not (dependencies[table_id] & remaining)
                ),
                key=lambda item: self._table_sort_key(model.table_by_id(item)),
            )
            if ready:
                ordered_ids.extend(ready)
                remaining.difference_update(ready)
                continue

            removable_edge: tuple[str, str] | None = None
            for edge in sorted(edges):
                source_id, target_id = edge
                if source_id not in remaining or target_id not in remaining:
                    continue
                foreign_keys = edges[edge]
                source = model.table_by_id(source_id)
                if all(
                    all(
                        source.column_by_id(column_id).nullable is not False
                        for column_id in foreign_key.column_ids
                    )
                    for foreign_key in foreign_keys
                ):
                    removable_edge = edge
                    nullable_cycle_foreign_keys.update(
                        foreign_key.id for foreign_key in foreign_keys
                    )
                    break
            if removable_edge is None:
                names = ", ".join(
                    sorted(model.table_by_id(item).name for item in remaining)
                )
                raise TestDataGenerationError(
                    (
                        TestDataIssue(
                            "Un cycle de clés étrangères obligatoires empêche une "
                            f"insertion sûre : {names}."
                        ),
                    )
                )
            source_id, target_id = removable_edge
            dependencies[source_id].discard(target_id)

        ordered = [model.table_by_id(item) for item in ordered_ids]
        ordered.extend(
            sorted(
                (table for table in model.tables if counts[table.id] == 0),
                key=self._table_sort_key,
            )
        )
        return ordered, nullable_cycle_foreign_keys

    def _generate_table_rows(
        self,
        table: MLDTable,
        count: int,
        model: MLDModel,
        rows_by_table: dict[str, list[dict[str, TestValue]]],
        null_foreign_keys: set[str],
    ) -> list[dict[str, TestValue]]:
        rows: list[dict[str, TestValue]] = []
        foreign_columns: dict[str, tuple[MLDForeignKey, int]] = {}
        for foreign_key in table.foreign_keys:
            for position, column_id in enumerate(foreign_key.column_ids):
                foreign_columns[column_id] = (foreign_key, position)

        foreign_strides: dict[str, int] = {}
        stride = 1
        for foreign_key in table.foreign_keys:
            target_id = foreign_key.referenced_table_id
            if foreign_key.id in null_foreign_keys or target_id == table.id:
                continue
            target_size = len(rows_by_table.get(target_id, ()))
            if target_size:
                foreign_strides[foreign_key.id] = stride
                stride *= target_size

        for row_index in range(count):
            row: dict[str, TestValue] = {}
            for column in table.columns:
                foreign = foreign_columns.get(column.id)
                if foreign is None:
                    row[column.id] = self._native_value(table, column, row_index)
                    continue
                foreign_key, position = foreign
                if foreign_key.id in null_foreign_keys:
                    row[column.id] = None
                    continue
                target_id = foreign_key.referenced_table_id
                if target_id == table.id:
                    target_column = table.column_by_id(
                        foreign_key.referenced_column_ids[position]
                    )
                    row[column.id] = self._native_value(table, target_column, row_index)
                    continue
                target_rows = rows_by_table.get(target_id, [])
                if not target_rows:
                    row[column.id] = None
                    continue
                foreign_stride = foreign_strides.get(foreign_key.id, 1)
                target_row = target_rows[
                    (row_index // foreign_stride) % len(target_rows)
                ]
                row[column.id] = target_row[foreign_key.referenced_column_ids[position]]
            rows.append(row)
        return rows

    def _generated_uniqueness_problem(
        self, table: MLDTable, rows: list[dict[str, TestValue]]
    ) -> TestDataIssue | None:
        constraints: list[tuple[str, tuple[str, ...]]] = []
        if table.primary_key:
            constraints.append(("clé primaire", table.primary_key))
        constraints.extend(
            ("contrainte UNIQUE", item.column_ids) for item in table.unique_constraints
        )
        for label, column_ids in constraints:
            seen: set[tuple[TestValue, ...]] = set()
            for row in rows:
                values = tuple(row[item] for item in column_ids)
                if any(value is None for value in values):
                    continue
                if values in seen:
                    return TestDataIssue(
                        f"La quantité demandée pour {table.name} dépasse les "
                        f"combinaisons disponibles pour sa {label}.",
                        table.id,
                    )
                seen.add(values)
        return None

    def _native_value(
        self, table: MLDTable, column: MLDColumn, row_index: int
    ) -> TestValue:
        ordinal = row_index + 1
        type_name = column.data_type.name
        if type_name in {MLDDataTypeName.INTEGER, MLDDataTypeName.BIGINT}:
            return ordinal
        if type_name is MLDDataTypeName.DECIMAL:
            scale = column.data_type.scale or 0
            precision = column.data_type.precision or 10
            integer_digits = max(1, precision - scale)
            maximum = max(1, (10**integer_digits) - 1)
            integer = ((ordinal - 1) % maximum) + 1
            return Decimal(integer).scaleb(-scale) if scale else Decimal(integer)
        if type_name is MLDDataTypeName.FLOAT:
            return ordinal + 0.25
        if type_name is MLDDataTypeName.BOOLEAN:
            return row_index % 2 == 0
        if type_name is MLDDataTypeName.DATE:
            return date(2025, 1, 1) + timedelta(days=row_index % 365)
        if type_name is MLDDataTypeName.TIME:
            return time(hour=row_index % 24, minute=(row_index * 7) % 60)
        if type_name in {MLDDataTypeName.DATETIME, MLDDataTypeName.TIMESTAMP}:
            return datetime(2025, 1, 1, 8, 0) + timedelta(hours=row_index)
        return self._text_value(table, column, ordinal)

    def _text_value(self, table: MLDTable, column: MLDColumn, ordinal: int) -> str:
        lowered = column.name.casefold()
        token = self._base36(ordinal)
        if "email" in lowered or "courriel" in lowered:
            value = f"utilisateur{token}@example.test"
        elif "telephone" in lowered or "phone" in lowered:
            value = f"+331000{ordinal:04d}"
        elif lowered in {"nom", "name"} or lowered.endswith("_nom"):
            value = f"{table.name.title()} {token}"
        elif "prenom" in lowered:
            value = f"Prenom {token}"
        elif "adresse" in lowered:
            value = f"{ordinal} rue Exemple"
        else:
            value = f"{column.name}_{token}"
        if column.data_type.name is MLDDataTypeName.VARCHAR:
            length = column.data_type.length or 100
            if len(value) > length:
                value = token[-length:].rjust(length, "0")
        return value

    def _render_insert(
        self,
        table: MLDTable,
        rows: list[dict[str, TestValue]],
        dialect: SQLDialect,
    ) -> str:
        columns = table.columns
        names = ", ".join(dialect.quote_identifier(item.name) for item in columns)
        value_rows = [
            "    ("
            + ", ".join(self._literal(row[column.id], dialect) for column in columns)
            + ")"
            for row in rows
        ]
        return (
            f"-- Table : {table.name} ({len(rows)} ligne(s))\n"
            f"INSERT INTO {dialect.quote_identifier(table.name)} ({names}) VALUES\n"
            + ",\n".join(value_rows)
            + ";\n"
        )

    @staticmethod
    def _literal(value: TestValue, dialect: SQLDialect) -> str:
        if value is None:
            return "NULL"
        if isinstance(value, bool):
            if dialect.target is SQLTarget.SQLITE:
                return "1" if value else "0"
            return "TRUE" if value else "FALSE"
        if isinstance(value, datetime):
            return f"'{value.isoformat(sep=' ')}'"
        if isinstance(value, (date, time)):
            return f"'{value.isoformat()}'"
        if isinstance(value, (int, float, Decimal)):
            return str(value)
        return "'" + value.replace("'", "''") + "'"

    def _warnings(
        self,
        model: MLDModel,
        cycle_foreign_keys: set[str],
        empty_target_foreign_keys: set[str],
    ) -> list[TestDataIssue]:
        warnings: list[TestDataIssue] = []
        for table in model.tables:
            if table.check_constraints:
                warnings.append(
                    TestDataIssue(
                        f"Les CHECK libres de {table.name} ne peuvent pas tous être "
                        "démontrés automatiquement ; vérifiez le script avant usage.",
                        table.id,
                    )
                )
            for foreign_key in table.foreign_keys:
                if foreign_key.id in cycle_foreign_keys:
                    target = model.table_by_id(foreign_key.referenced_table_id)
                    warnings.append(
                        TestDataIssue(
                            f"La FK facultative {table.name} → {target.name} a été "
                            "mise à NULL pour rompre un cycle.",
                            table.id,
                        )
                    )
                elif foreign_key.id in empty_target_foreign_keys:
                    target = model.table_by_id(foreign_key.referenced_table_id)
                    warnings.append(
                        TestDataIssue(
                            f"La FK facultative {table.name} → {target.name} a été "
                            "mise à NULL car aucune ligne cible n'est demandée.",
                            table.id,
                        )
                    )
        return warnings

    @staticmethod
    def _base36(value: int) -> str:
        alphabet = "0123456789abcdefghijklmnopqrstuvwxyz"
        output = ""
        current = value
        while current:
            current, remainder = divmod(current, 36)
            output = alphabet[remainder] + output
        return output or "0"

    @staticmethod
    def _table_sort_key(table: MLDTable) -> tuple[str, str]:
        return table.name.casefold(), table.id
