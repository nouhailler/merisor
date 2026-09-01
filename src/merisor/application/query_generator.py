"""Génération explicable de requêtes SELECT exclusivement depuis le MLD."""

from __future__ import annotations

import re
import unicodedata
from collections import deque
from dataclasses import dataclass
from enum import Enum

from merisor.application.sql_generator import SQLDialect, SQLTarget, sql_dialect
from merisor.domain import MLDColumn, MLDDataTypeName, MLDForeignKey, MLDModel, MLDTable


class QueryTarget(str, Enum):
    POSTGRESQL = "postgresql"
    SQLITE = "sqlite"
    MYSQL = "mysql"
    MARIADB = "mariadb"

    @property
    def display_name(self) -> str:
        return {
            QueryTarget.POSTGRESQL: "PostgreSQL",
            QueryTarget.SQLITE: "SQLite",
            QueryTarget.MYSQL: "MySQL",
            QueryTarget.MARIADB: "MariaDB",
        }[self]

    @property
    def sql_target(self) -> SQLTarget:
        if self is QueryTarget.MARIADB:
            return SQLTarget.MYSQL
        return SQLTarget(self.value)


@dataclass(frozen=True, slots=True)
class QueryGenerationResult:
    sql: str
    used_tables: tuple[str, ...]
    explanation: tuple[str, ...]
    warnings: tuple[str, ...]
    target: QueryTarget


class QueryGenerationError(ValueError):
    def __init__(self, problems: tuple[str, ...]) -> None:
        self.problems = problems
        super().__init__(
            f"Impossible de générer la requête : {len(problems)} problème(s)."
        )


@dataclass(frozen=True, slots=True)
class _JoinEdge:
    child_table_id: str
    parent_table_id: str
    foreign_key: MLDForeignKey

    def other(self, table_id: str) -> str:
        return (
            self.parent_table_id
            if table_id == self.child_table_id
            else self.child_table_id
        )


class SQLQueryGenerator:
    """Transforme une intention simple en SELECT vérifiable et déterministe."""

    _AGGREGATE_TERMS = frozenset(
        {"total", "totale", "totaux", "somme", "montant", "chiffre affaires"}
    )
    _COUNT_TERMS = frozenset({"nombre", "combien", "compter", "count"})
    _RANKING_TERMS = frozenset(
        {"meilleur", "meilleurs", "premier", "premiers", "top", "classement"}
    )
    _METRIC_TERMS = (
        "montant",
        "total",
        "prix",
        "cout",
        "coût",
        "valeur",
        "chiffre",
        "solde",
    )
    _DISPLAY_TERMS = ("nom", "libelle", "libellé", "titre", "email", "courriel")
    _NUMERIC_TYPES = frozenset(
        {
            MLDDataTypeName.INTEGER,
            MLDDataTypeName.BIGINT,
            MLDDataTypeName.DECIMAL,
            MLDDataTypeName.FLOAT,
        }
    )

    def generate(
        self,
        model: MLDModel,
        description: str,
        target: QueryTarget | str,
    ) -> QueryGenerationResult:
        normalized_target = QueryTarget(target)
        dialect = sql_dialect(normalized_target.sql_target)
        normalized_description = self._normalize(description)
        if not normalized_description:
            raise QueryGenerationError(("Décrivez la requête à produire.",))
        if not model.tables:
            raise QueryGenerationError(("Le MLD ne contient aucune table.",))

        mentioned = self._mentioned_tables(model, normalized_description)
        if not mentioned:
            raise QueryGenerationError(
                (
                    "Aucune table du MLD n'a été reconnue dans la description. "
                    "Utilisez au moins un nom d'entité ou de table.",
                )
            )
        base = self._base_table(mentioned, normalized_description)
        measure = self._measure_column(model, normalized_description, mentioned)
        count_requested = self._contains_any(normalized_description, self._COUNT_TERMS)
        aggregate_requested = self._contains_any(
            normalized_description, self._AGGREGATE_TERMS
        )
        ranking_requested = self._contains_any(
            normalized_description, self._RANKING_TERMS
        )

        required_ids = {table.id for table in mentioned}
        if measure is not None:
            required_ids.add(measure[0].id)
        graph = self._join_graph(model)
        joined, joins = self._connect_required_tables(base, required_ids, graph, model)
        aliases = {table.id: f"t{index + 1}" for index, table in enumerate(joined)}
        limit = self._extract_limit(normalized_description)
        warnings: list[str] = []
        explanation = [f"Table principale reconnue : {base.name}."]

        select_items: list[str]
        group_items: list[str] = []
        order_expression: str | None = None
        if aggregate_requested or ranking_requested or count_requested:
            dimensions = self._dimension_columns(base)
            if not dimensions:
                raise QueryGenerationError(
                    (f"La table {base.name} ne possède aucune colonne exploitable.",)
                )
            select_items = [
                self._qualified(column, aliases[base.id], dialect)
                for column in dimensions
            ]
            group_items.extend(select_items)
            if measure is not None and (aggregate_requested or ranking_requested):
                measure_table, measure_column = measure
                qualified_measure = self._qualified(
                    measure_column, aliases[measure_table.id], dialect
                )
                aggregate = f"SUM({qualified_measure})"
                alias = dialect.quote_identifier(f"total_{measure_column.name}")
                select_items.append(f"{aggregate} AS {alias}")
                order_expression = aggregate
                explanation.append(
                    f"Mesure reconnue : somme de {measure_table.name}."
                    f"{measure_column.name}."
                )
            elif count_requested or ranking_requested:
                if ranking_requested and not count_requested and len(mentioned) == 1:
                    raise QueryGenerationError(
                        (
                            "Le classement demandé ne précise aucune mesure ni "
                            "table à compter.",
                        )
                    )
                count_table = next(
                    (table for table in mentioned if table.id != base.id), base
                )
                count_expression = self._count_expression(
                    count_table, aliases[count_table.id], dialect
                )
                alias = dialect.quote_identifier(f"nombre_{count_table.name.lower()}")
                select_items.append(f"{count_expression} AS {alias}")
                order_expression = count_expression
                explanation.append(f"Mesure reconnue : nombre de {count_table.name}.")
                if aggregate_requested and measure is None:
                    warnings.append(
                        "Aucune colonne monétaire explicite n'a été trouvée ; "
                        "un comptage a été utilisé à la place."
                    )
            else:
                raise QueryGenerationError(
                    (
                        "Une somme ou un classement est demandé, mais aucune "
                        "colonne numérique métier n'a été reconnue.",
                    )
                )
        else:
            select_items = [f"{aliases[table.id]}.*" for table in mentioned]
            warnings.append(
                "Aucun agrégat ou filtre structuré n'a été reconnu ; toutes les "
                "colonnes des tables nommées sont sélectionnées."
            )

        lines = ["SELECT", "    " + ",\n    ".join(select_items)]
        lines.append(
            f"FROM {dialect.quote_identifier(base.name)} AS {aliases[base.id]}"
        )
        for edge, next_table_id in joins:
            next_table = model.table_by_id(next_table_id)
            condition = self._join_condition(edge, aliases, model, dialect)
            lines.append(
                f"JOIN {dialect.quote_identifier(next_table.name)} AS "
                f"{aliases[next_table.id]} ON {condition}"
            )
        if group_items:
            lines.append("GROUP BY " + ", ".join(group_items))
        if order_expression is not None:
            lines.append(f"ORDER BY {order_expression} DESC")
        if limit is not None:
            lines.append(f"LIMIT {limit}")
            explanation.append(f"Limite reconnue : {limit} résultat(s).")
        elif ranking_requested:
            lines.append("LIMIT 10")
            explanation.append("Aucune limite explicite : 10 résultats retenus.")
        lines[-1] += ";"

        used_tables = tuple(table.name for table in joined)
        explanation.append(
            "Jointures dérivées uniquement des clés étrangères présentes dans le MLD."
        )
        return QueryGenerationResult(
            sql="\n".join(lines) + "\n",
            used_tables=used_tables,
            explanation=tuple(explanation),
            warnings=tuple(warnings),
            target=normalized_target,
        )

    def _mentioned_tables(self, model: MLDModel, description: str) -> list[MLDTable]:
        matches: list[tuple[int, str, MLDTable]] = []
        for table in model.tables:
            normalized_name = self._normalize(table.name).replace("_", " ")
            variants = {normalized_name, normalized_name.replace(" ", "_")}
            variants.update(self._plural_variants(normalized_name))
            positions = [
                position
                for variant in variants
                if (position := self._phrase_position(description, variant)) >= 0
            ]
            if positions:
                matches.append((min(positions), table.name.casefold(), table))
        return [item[2] for item in sorted(matches, key=lambda item: item[:2])]

    def _base_table(self, mentioned: list[MLDTable], description: str) -> MLDTable:
        for table in mentioned:
            name = self._normalize(table.name).replace("_", " ")
            variants = {name, *self._plural_variants(name)}
            for variant in variants:
                if re.search(
                    rf"\b(?:par|pour chaque|pour chacun des)\s+"
                    rf"{re.escape(variant)}\b",
                    description,
                ):
                    return table
        return mentioned[0]

    def _measure_column(
        self,
        model: MLDModel,
        description: str,
        mentioned: list[MLDTable],
    ) -> tuple[MLDTable, MLDColumn] | None:
        mentioned_ids = {table.id for table in mentioned}
        candidates: list[tuple[int, int, str, MLDTable, MLDColumn]] = []
        for table in model.tables:
            for column in table.columns:
                if column.data_type.name not in self._NUMERIC_TYPES:
                    continue
                if table.is_primary_key(column.id) or table.is_foreign_key(column.id):
                    continue
                name = self._normalize(column.name).replace("_", " ")
                exact_position = self._phrase_position(description, name)
                semantic = next(
                    (
                        index
                        for index, term in enumerate(self._METRIC_TERMS)
                        if term in name and term in description
                    ),
                    len(self._METRIC_TERMS) + 1,
                )
                if exact_position < 0 and semantic > len(self._METRIC_TERMS):
                    continue
                candidates.append(
                    (
                        0 if exact_position >= 0 else 1,
                        0 if table.id in mentioned_ids else 1,
                        f"{table.name.casefold()}.{column.name.casefold()}",
                        table,
                        column,
                    )
                )
        if not candidates:
            return None
        selected = min(candidates, key=lambda item: item[:3])
        return selected[3], selected[4]

    def _connect_required_tables(
        self,
        base: MLDTable,
        required_ids: set[str],
        graph: dict[str, list[_JoinEdge]],
        model: MLDModel,
    ) -> tuple[list[MLDTable], list[tuple[_JoinEdge, str]]]:
        included = {base.id}
        ordered = [base]
        joins: list[tuple[_JoinEdge, str]] = []
        for target_id in sorted(
            required_ids - {base.id},
            key=lambda item: self._table_key(model.table_by_id(item)),
        ):
            if target_id in included:
                continue
            path = self._shortest_path(included, target_id, graph, model)
            if path is None:
                raise QueryGenerationError(
                    (
                        f"Aucune chaîne de clés étrangères ne relie {base.name} "
                        f"à {model.table_by_id(target_id).name}.",
                    )
                )
            current_id = path[0][0]
            for source_id, edge in path:
                if source_id != current_id:
                    current_id = source_id
                next_id = edge.other(source_id)
                if next_id not in included:
                    joins.append((edge, next_id))
                    included.add(next_id)
                    ordered.append(model.table_by_id(next_id))
                current_id = next_id
        return ordered, joins

    def _shortest_path(
        self,
        starts: set[str],
        target_id: str,
        graph: dict[str, list[_JoinEdge]],
        model: MLDModel,
    ) -> list[tuple[str, _JoinEdge]] | None:
        queue: deque[str] = deque(
            sorted(starts, key=lambda item: self._table_key(model.table_by_id(item)))
        )
        previous: dict[str, tuple[str, _JoinEdge] | None] = dict.fromkeys(starts)
        while queue:
            current = queue.popleft()
            if current == target_id:
                break
            edges = sorted(
                graph.get(current, ()),
                key=lambda edge: self._table_key(
                    model.table_by_id(edge.other(current))
                ),
            )
            for edge in edges:
                neighbor = edge.other(current)
                if neighbor in previous:
                    continue
                previous[neighbor] = (current, edge)
                queue.append(neighbor)
        if target_id not in previous:
            return None
        reversed_path: list[tuple[str, _JoinEdge]] = []
        current = target_id
        while previous[current] is not None:
            step = previous[current]
            if step is None:
                break
            parent, edge = step
            reversed_path.append((parent, edge))
            current = parent
        return list(reversed(reversed_path))

    @staticmethod
    def _join_graph(model: MLDModel) -> dict[str, list[_JoinEdge]]:
        graph: dict[str, list[_JoinEdge]] = {table.id: [] for table in model.tables}
        for table in model.tables:
            for foreign_key in table.foreign_keys:
                edge = _JoinEdge(table.id, foreign_key.referenced_table_id, foreign_key)
                graph[table.id].append(edge)
                graph[foreign_key.referenced_table_id].append(edge)
        return graph

    @staticmethod
    def _join_condition(
        edge: _JoinEdge,
        aliases: dict[str, str],
        model: MLDModel,
        dialect: SQLDialect,
    ) -> str:
        child = model.table_by_id(edge.child_table_id)
        parent = model.table_by_id(edge.parent_table_id)
        conditions = []
        for local_id, distant_id in zip(
            edge.foreign_key.column_ids,
            edge.foreign_key.referenced_column_ids,
            strict=True,
        ):
            local = child.column_by_id(local_id)
            distant = parent.column_by_id(distant_id)
            conditions.append(
                f"{aliases[child.id]}.{dialect.quote_identifier(local.name)} = "
                f"{aliases[parent.id]}.{dialect.quote_identifier(distant.name)}"
            )
        return " AND ".join(conditions)

    def _dimension_columns(self, table: MLDTable) -> list[MLDColumn]:
        columns = list(table.primary_key_columns)
        display = next(
            (
                column
                for term in self._DISPLAY_TERMS
                for column in table.columns
                if term in self._normalize(column.name)
                and column.id not in table.primary_key
            ),
            None,
        )
        if display is not None:
            columns.append(display)
        return columns or table.columns[:1]

    @staticmethod
    def _count_expression(table: MLDTable, alias: str, dialect: SQLDialect) -> str:
        if table.primary_key:
            column = table.column_by_id(table.primary_key[0])
            return f"COUNT({alias}.{dialect.quote_identifier(column.name)})"
        return "COUNT(*)"

    @staticmethod
    def _qualified(column: MLDColumn, alias: str, dialect: SQLDialect) -> str:
        return f"{alias}.{dialect.quote_identifier(column.name)}"

    @staticmethod
    def _extract_limit(description: str) -> int | None:
        patterns = (
            r"\btop\s+(\d+)\b",
            r"\b(\d+)\s+(?:meilleur|meilleurs|premier|premiers)\b",
            r"\blimite\s+(?:a\s+)?(\d+)\b",
        )
        for pattern in patterns:
            if match := re.search(pattern, description):
                return min(10_000, max(1, int(match.group(1))))
        return None

    @staticmethod
    def _contains_any(description: str, terms: frozenset[str]) -> bool:
        return any(
            SQLQueryGenerator._phrase_position(description, term) >= 0 for term in terms
        )

    @staticmethod
    def _phrase_position(description: str, phrase: str) -> int:
        match = re.search(rf"(?<!\w){re.escape(phrase)}(?!\w)", description)
        return -1 if match is None else match.start()

    @staticmethod
    def _plural_variants(name: str) -> set[str]:
        words = name.split()
        if not words:
            return set()
        variants = {name + "s"}
        variants.add(" ".join((*words[:-1], words[-1] + "s")))
        variants.add(" ".join((*words[:-1], words[-1] + "x")))
        return variants

    @staticmethod
    def _normalize(value: str) -> str:
        decomposed = unicodedata.normalize("NFKD", value.casefold())
        without_accents = "".join(
            character
            for character in decomposed
            if not unicodedata.combining(character)
        )
        return re.sub(r"\s+", " ", without_accents.replace("-", " ")).strip()

    @staticmethod
    def _table_key(table: MLDTable) -> tuple[str, str]:
        return table.name.casefold(), table.id
