"""Reverse-engineering déterministe d'un DDL PostgreSQL/SQLite vers MLD et MCD."""

from __future__ import annotations

import re
from dataclasses import dataclass

from merisor.domain import (
    Association,
    Attribute,
    Cardinality,
    Entity,
    Inheritance,
    InheritanceStrategy,
    MCDModel,
    MLDCheckConstraint,
    MLDColumn,
    MLDDataType,
    MLDDataTypeName,
    MLDForeignKey,
    MLDIndex,
    MLDModel,
    MLDReferentialAction,
    MLDTable,
    MLDTableSource,
    MLDUniqueConstraint,
    Position,
    Relation,
)


class DDLImportError(ValueError):
    """Le texte DDL ne peut pas être converti sans ambiguïté structurelle."""

    def __init__(self, problems: str | list[str]) -> None:
        self.problems = (problems,) if isinstance(problems, str) else tuple(problems)
        super().__init__("\n".join(self.problems))


@dataclass(frozen=True, slots=True)
class DDLImportResult:
    mld: MLDModel
    mcd: MCDModel
    warnings: tuple[str, ...] = ()


@dataclass(slots=True)
class _PendingForeignKey:
    table: MLDTable
    local_names: tuple[str, ...]
    target_name: str
    target_names: tuple[str, ...]
    name: str | None = None
    on_delete: MLDReferentialAction | None = None
    on_update: MLDReferentialAction | None = None


class SQLDDLImporter:
    """Parse un sous-ensemble portable et courant des DDL SQLite/PostgreSQL."""

    def import_text(self, sql: str) -> DDLImportResult:
        if not isinstance(sql, str) or not sql.strip():
            raise DDLImportError("Le fichier SQL est vide.")
        cleaned = self._remove_comments(sql)
        statements = self._split_top_level(cleaned, ";")
        tables: list[MLDTable] = []
        by_name: dict[str, MLDTable] = {}
        pending: list[_PendingForeignKey] = []
        deferred_indexes: list[str] = []
        warnings: list[str] = []

        for statement in statements:
            text = statement.strip()
            if not text:
                continue
            if re.match(r"(?is)^CREATE\s+TABLE\b", text):
                table, foreign_keys = self._parse_create_table(text, len(tables))
                key = table.name.casefold()
                if key in by_name:
                    raise DDLImportError(
                        f'La table "{table.name}" est déclarée deux fois.'
                    )
                tables.append(table)
                by_name[key] = table
                pending.extend(foreign_keys)
            elif re.match(r"(?is)^CREATE\s+(?:UNIQUE\s+)?INDEX\b", text):
                deferred_indexes.append(text)
            elif re.match(r"(?is)^ALTER\s+TABLE\b", text):
                pending.append(self._parse_alter_foreign_key(text, by_name))
            elif re.match(r"(?is)^(PRAGMA|SET|BEGIN|COMMIT)\b", text):
                continue
            else:
                warnings.append(
                    "Instruction ignorée (seuls CREATE TABLE, CREATE INDEX et "
                    f"ALTER TABLE … FOREIGN KEY sont importés) : {text[:70]}"
                )

        if not tables:
            raise DDLImportError("Aucune instruction CREATE TABLE exploitable trouvée.")
        self._resolve_foreign_keys(pending, by_name)
        for statement in deferred_indexes:
            self._parse_index(statement, by_name)
        missing_pk = [table.name for table in tables if not table.primary_key]
        if missing_pk:
            raise DDLImportError(
                "Chaque table doit posséder une clé primaire pour reconstruire "
                "un MCD. PK absente : " + ", ".join(missing_pk)
            )
        mld = MLDModel(tables, generated_from_fingerprint="ddl-import")
        mcd, reverse_warnings = self._to_mcd(mld)
        return DDLImportResult(mld, mcd, (*warnings, *reverse_warnings))

    def _parse_create_table(
        self, statement: str, table_index: int
    ) -> tuple[MLDTable, list[_PendingForeignKey]]:
        match = re.match(
            r"(?is)^CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(.+?)\s*\(",
            statement,
        )
        if match is None:
            raise DDLImportError("Instruction CREATE TABLE invalide.")
        table_name = self._identifier(match.group(1))
        open_index = statement.find("(", match.start())
        close_index = self._matching_parenthesis(statement, open_index)
        body = statement[open_index + 1 : close_index]
        table = MLDTable(
            id=f"table:ddl:{table_index}",
            name=table_name,
            source_element_id=f"ddl:table:{table_index}",
            source=MLDTableSource.ENTITY,
        )
        primary_names: list[str] = []
        unique_names: list[tuple[str, ...]] = []
        checks: list[str] = []
        foreign_specs: list[
            tuple[
                tuple[str, ...],
                str,
                tuple[str, ...],
                str | None,
                MLDReferentialAction | None,
                MLDReferentialAction | None,
            ]
        ] = []
        for definition in self._split_top_level(body, ","):
            part = definition.strip()
            if not part:
                continue
            constraint_name, core = self._strip_constraint_name(part)
            upper = core.lstrip().upper()
            if upper.startswith("PRIMARY KEY"):
                primary_names.extend(self._parenthesized_names(core))
            elif upper.startswith("FOREIGN KEY"):
                foreign_specs.append(self._foreign_key_spec(core, constraint_name))
            elif upper.startswith("UNIQUE"):
                unique_names.append(self._parenthesized_names(core))
            elif upper.startswith("CHECK"):
                checks.append(self._parenthesized_content(core))
            else:
                column, inline_pk, inline_unique, inline_fk, inline_checks = (
                    self._parse_column(part, table, len(table.columns))
                )
                table.columns.append(column)
                if inline_pk:
                    primary_names.append(column.name)
                if inline_unique:
                    unique_names.append((column.name,))
                if inline_fk is not None:
                    foreign_specs.append(
                        (
                            (column.name,),
                            inline_fk[0],
                            inline_fk[1],
                            constraint_name,
                            inline_fk[2],
                            inline_fk[3],
                        )
                    )
                checks.extend(inline_checks)

        table.primary_key = self._column_ids(table, tuple(primary_names), "PK")
        for index, names in enumerate(unique_names):
            table.unique_constraints.append(
                MLDUniqueConstraint(
                    id=f"unique:ddl:{table_index}:{index}",
                    column_ids=self._column_ids(table, names, "UNIQUE"),
                    source_association_id=f"ddl:unique:{table_index}:{index}",
                )
            )
        for index, expression in enumerate(checks):
            table.check_constraints.append(
                MLDCheckConstraint(
                    id=f"check:ddl:{table_index}:{index}",
                    expression=expression,
                    source_element_id=table.source_element_id,
                )
            )
        pending = [
            _PendingForeignKey(table, local, target, remote, name, on_delete, on_update)
            for local, target, remote, name, on_delete, on_update in foreign_specs
        ]
        return table, pending

    def _parse_column(
        self, definition: str, table: MLDTable, column_index: int
    ) -> tuple[
        MLDColumn,
        bool,
        bool,
        tuple[
            str,
            tuple[str, ...],
            MLDReferentialAction | None,
            MLDReferentialAction | None,
        ]
        | None,
        list[str],
    ]:
        name_token, remainder = self._take_identifier(definition)
        name = self._identifier(name_token)
        type_match = re.match(
            r"(?is)^\s*([A-Z][A-Z0-9_ ]*(?:\s*\([^)]*\))?)", remainder
        )
        if type_match is None:
            raise DDLImportError(f"Type absent pour {table.name}.{name}.")
        raw_type = type_match.group(1).strip()
        # Le type s'arrête avant le premier mot de contrainte.
        raw_type = re.split(
            r"(?i)\s+(?=PRIMARY\s+KEY|NOT\s+NULL|NULL\b|UNIQUE\b|REFERENCES\b|CHECK\b|DEFAULT\b|GENERATED\b)",
            raw_type,
            maxsplit=1,
        )[0]
        constraints = remainder[type_match.start() + len(raw_type) :]
        data_type, serial = self._logical_type(raw_type)
        inline_pk = bool(re.search(r"(?i)\bPRIMARY\s+KEY\b", constraints))
        nullable = not bool(re.search(r"(?i)\bNOT\s+NULL\b", constraints))
        if inline_pk:
            nullable = False
        inline_unique = bool(re.search(r"(?i)\bUNIQUE\b", constraints))
        auto_increment = serial or bool(
            re.search(r"(?i)\bAUTOINCREMENT\b|\bGENERATED\b.+\bIDENTITY\b", constraints)
        )
        reference = re.search(
            r"(?is)\bREFERENCES\s+([^\s(]+)\s*\(([^)]*)\)", constraints
        )
        inline_fk = None
        if reference is not None:
            on_delete, on_update = self._referential_actions(constraints)
            inline_fk = (
                self._identifier(reference.group(1)),
                tuple(
                    self._identifier(item)
                    for item in self._split_top_level(reference.group(2), ",")
                ),
                on_delete,
                on_update,
            )
        checks = [
            item.strip()
            for item in re.findall(r"(?is)\bCHECK\s*\(([^)]*)\)", constraints)
        ]
        default_match = re.search(
            r"(?is)\bDEFAULT\s+('(?:''|[^'])*'|\"(?:\"\"|[^\"])*\"|[^\s,]+)",
            constraints,
        )
        return (
            MLDColumn(
                id=f"column:ddl:{table.id}:{column_index}",
                name=name,
                nullable=nullable,
                data_type=data_type,
                default=default_match.group(1) if default_match else None,
                source_element_id=table.source_element_id,
                auto_increment=auto_increment,
            ),
            inline_pk,
            inline_unique,
            inline_fk,
            checks,
        )

    def _resolve_foreign_keys(
        self, pending: list[_PendingForeignKey], by_name: dict[str, MLDTable]
    ) -> None:
        for index, item in enumerate(pending):
            target = by_name.get(item.target_name.casefold())
            if target is None:
                raise DDLImportError(
                    f"La FK de {item.table.name} référence la table absente "
                    f"{item.target_name}."
                )
            local_ids = self._column_ids(item.table, item.local_names, "FK")
            target_ids = self._column_ids(target, item.target_names, "FK cible")
            item.table.foreign_keys.append(
                MLDForeignKey(
                    id=f"fk:ddl:{item.table.id}:{index}",
                    name=item.name,
                    column_ids=local_ids,
                    referenced_table_id=target.id,
                    referenced_column_ids=target_ids,
                    source_association_id=f"ddl:fk:{item.table.id}:{index}",
                    on_delete=item.on_delete,
                    on_update=item.on_update,
                )
            )

    def _parse_alter_foreign_key(
        self, statement: str, by_name: dict[str, MLDTable]
    ) -> _PendingForeignKey:
        match = re.match(
            r"(?is)^ALTER\s+TABLE\s+(.+?)\s+ADD\s+(?:CONSTRAINT\s+(.+?)\s+)?"
            r"FOREIGN\s+KEY\s*\(([^)]*)\)\s+REFERENCES\s+([^\s(]+)\s*\(([^)]*)\)",
            statement,
        )
        if match is None:
            raise DDLImportError("ALTER TABLE non pris en charge ou invalide.")
        table_name = self._identifier(match.group(1))
        table = by_name.get(table_name.casefold())
        if table is None:
            raise DDLImportError(
                f"ALTER TABLE référence la table absente {table_name}."
            )
        on_delete, on_update = self._referential_actions(statement)
        return _PendingForeignKey(
            table,
            tuple(
                self._identifier(item)
                for item in self._split_top_level(match.group(3), ",")
            ),
            self._identifier(match.group(4)),
            tuple(
                self._identifier(item)
                for item in self._split_top_level(match.group(5), ",")
            ),
            self._identifier(match.group(2)) if match.group(2) else None,
            on_delete,
            on_update,
        )

    def _parse_index(self, statement: str, by_name: dict[str, MLDTable]) -> None:
        match = re.match(
            r"(?is)^CREATE\s+(UNIQUE\s+)?INDEX\s+(.+?)\s+ON\s+(.+?)\s*\(([^)]*)\)",
            statement,
        )
        if match is None:
            raise DDLImportError("Instruction CREATE INDEX invalide.")
        table_name = self._identifier(match.group(3))
        table = by_name.get(table_name.casefold())
        if table is None:
            raise DDLImportError(f"L'index référence la table absente {table_name}.")
        names = tuple(
            self._identifier(item)
            for item in self._split_top_level(match.group(4), ",")
        )
        table.indexes.append(
            MLDIndex(
                id=f"index:ddl:{table.id}:{len(table.indexes)}",
                name=self._identifier(match.group(2)),
                column_ids=self._column_ids(table, names, "index"),
                unique=bool(match.group(1)),
            )
        )

    def _to_mcd(self, mld: MLDModel) -> tuple[MCDModel, list[str]]:
        model = MCDModel()
        warnings = [
            "Le MCD est une reconstruction heuristique : les cardinalités minimales "
            "et les intentions conceptuelles absentes du DDL doivent être vérifiées."
        ]
        fk_columns = {
            table.id: {
                column_id for fk in table.foreign_keys for column_id in fk.column_ids
            }
            for table in mld.tables
        }
        inheritance_fk: dict[str, MLDForeignKey] = {}
        for table in mld.tables:
            for fk in table.foreign_keys:
                if set(fk.column_ids) == set(table.primary_key):
                    inheritance_fk[table.id] = fk
                    break
        join_tables = {
            table.id
            for table in mld.tables
            if len(table.foreign_keys) >= 2
            and set(table.primary_key)
            == {column_id for fk in table.foreign_keys for column_id in fk.column_ids}
        }
        entities: dict[str, Entity] = {}
        for index, table in enumerate(mld.tables):
            if table.id in join_tables:
                continue
            inherited = inheritance_fk.get(table.id)
            inherited_ids = set(inherited.column_ids) if inherited else set()
            attributes = [
                Attribute(
                    column.name,
                    identifier=column.id in table.primary_key,
                    id=f"attribute:ddl:{table.id}:{column.id}",
                    data_type=column.data_type,
                    nullable=column.nullable,
                    default=column.default,
                    unique=table.is_unique(column.id),
                    comment=column.comment,
                    auto_increment=column.auto_increment,
                    constraints=tuple(
                        check.expression
                        for check in table.check_constraints
                        if re.search(
                            rf"(?i)(?<!\w){re.escape(column.name)}(?!\w)",
                            check.expression,
                        )
                    ),
                )
                for column in table.columns
                if column.id not in fk_columns[table.id] or column.id in inherited_ids
            ]
            entity = Entity(
                table.name,
                Position((index % 4) * 330.0, (index // 4) * 230.0),
                id=f"entity:ddl:{table.id}",
                attributes=attributes,
            )
            model.add_entity(entity)
            entities[table.id] = entity

        for table_id, fk in inheritance_fk.items():
            if table_id in join_tables or fk.referenced_table_id not in entities:
                continue
            model.add_inheritance(
                Inheritance(
                    entities[fk.referenced_table_id].id,
                    (entities[table_id].id,),
                    InheritanceStrategy.JOINED,
                    id=f"inheritance:ddl:{table_id}",
                )
            )

        for table in mld.tables:
            if table.id in join_tables:
                association = Association(
                    table.name,
                    id=f"association:ddl:{table.id}",
                    attributes=[
                        Attribute(
                            column.name,
                            identifier=column.id in table.primary_key,
                            id=f"attribute:ddl:{table.id}:{column.id}",
                            data_type=column.data_type,
                            nullable=column.nullable,
                            default=column.default,
                            unique=table.is_unique(column.id),
                            comment=column.comment,
                            auto_increment=column.auto_increment,
                            constraints=tuple(
                                check.expression
                                for check in table.check_constraints
                                if re.search(
                                    rf"(?i)(?<!\w){re.escape(column.name)}(?!\w)",
                                    check.expression,
                                )
                            ),
                        )
                        for column in table.columns
                        if column.id not in fk_columns[table.id]
                    ],
                )
                model.add_association(association)
                for fk_index, fk in enumerate(table.foreign_keys):
                    target = entities.get(fk.referenced_table_id)
                    if target is None:
                        continue
                    role = ""
                    if (
                        sum(
                            1
                            for item in table.foreign_keys
                            if item.referenced_table_id == fk.referenced_table_id
                        )
                        > 1
                    ):
                        role = "_".join(
                            table.column_by_id(item).name for item in fk.column_ids
                        )
                    model.add_relation(
                        Relation(
                            target.id,
                            association.id,
                            id=f"relation:ddl:{table.id}:{fk_index}",
                            cardinality=Cardinality("0", "N"),
                            role=role,
                        )
                    )
                continue
            if table.id not in entities:
                continue
            for fk_index, fk in enumerate(table.foreign_keys):
                if inheritance_fk.get(table.id) is fk:
                    continue
                target = entities.get(fk.referenced_table_id)
                if target is None:
                    continue
                holder = entities[table.id]
                association = Association(
                    f"FK_{table.name}_{mld.table_by_id(fk.referenced_table_id).name}_{fk_index + 1}",
                    id=f"association:ddl:fk:{table.id}:{fk_index}",
                )
                model.add_association(association)
                nullable = any(
                    table.column_by_id(item).nullable is not False
                    for item in fk.column_ids
                )
                reflexive = target.id == holder.id
                model.add_relation(
                    Relation(
                        target.id,
                        association.id,
                        id=f"relation:ddl:fk:{table.id}:{fk_index}:target",
                        cardinality=Cardinality("0", "N"),
                        role="référencé" if reflexive else "",
                    )
                )
                model.add_relation(
                    Relation(
                        holder.id,
                        association.id,
                        id=f"relation:ddl:fk:{table.id}:{fk_index}:holder",
                        cardinality=Cardinality("0" if nullable else "1", "1"),
                        role="porteur" if reflexive else "",
                    )
                )
        return model, warnings

    @staticmethod
    def _logical_type(raw: str) -> tuple[MLDDataType, bool]:
        normalized = re.sub(r"\s+", " ", raw.strip().upper())
        params = re.search(r"\(([^)]*)\)", normalized)
        base = normalized.split("(", 1)[0].strip()
        serial = base in {"SERIAL", "BIGSERIAL"}
        if base in {"BIGINT", "INT8", "BIGSERIAL"}:
            return MLDDataType(MLDDataTypeName.BIGINT), serial
        if base in {"INT", "INTEGER", "INT2", "INT4", "SMALLINT", "SERIAL"}:
            return MLDDataType(MLDDataTypeName.INTEGER), serial
        if base in {"DECIMAL", "NUMERIC"}:
            values = (
                [int(item.strip()) for item in params.group(1).split(",")]
                if params
                else []
            )
            return MLDDataType(
                MLDDataTypeName.DECIMAL,
                precision=values[0] if values else None,
                scale=values[1] if len(values) > 1 else None,
            ), False
        if base in {"REAL", "FLOAT", "DOUBLE", "DOUBLE PRECISION"}:
            return MLDDataType(MLDDataTypeName.FLOAT), False
        if base in {"BOOL", "BOOLEAN"}:
            return MLDDataType(MLDDataTypeName.BOOLEAN), False
        if base in {"CHAR", "CHARACTER", "VARCHAR", "CHARACTER VARYING"}:
            length = int(params.group(1)) if params else 255
            return MLDDataType.varchar(length), False
        mapping = {
            "TEXT": MLDDataTypeName.TEXT,
            "CLOB": MLDDataTypeName.TEXT,
            "DATE": MLDDataTypeName.DATE,
            "TIME": MLDDataTypeName.TIME,
            "TIMESTAMP": MLDDataTypeName.TIMESTAMP,
            "TIMESTAMP WITHOUT TIME ZONE": MLDDataTypeName.TIMESTAMP,
            "TIMESTAMP WITH TIME ZONE": MLDDataTypeName.TIMESTAMP,
            "DATETIME": MLDDataTypeName.DATETIME,
        }
        if base in mapping:
            return MLDDataType(mapping[base]), False
        raise DDLImportError(f"Type SQL non pris en charge : {raw}.")

    @staticmethod
    def _remove_comments(sql: str) -> str:
        without_blocks = re.sub(r"(?s)/\*.*?\*/", " ", sql)
        return re.sub(r"(?m)--[^\n]*$", " ", without_blocks)

    @staticmethod
    def _split_top_level(text: str, delimiter: str) -> list[str]:
        result: list[str] = []
        start = 0
        depth = 0
        quote: str | None = None
        index = 0
        while index < len(text):
            char = text[index]
            if quote is not None:
                if char == quote:
                    if index + 1 < len(text) and text[index + 1] == quote:
                        index += 1
                    else:
                        quote = None
            elif char in {'"', "'", "`"}:
                quote = char
            elif char == "[":
                quote = "]"
            elif char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
            elif char == delimiter and depth == 0:
                result.append(text[start:index])
                start = index + 1
            index += 1
        result.append(text[start:])
        return result

    @staticmethod
    def _matching_parenthesis(text: str, start: int) -> int:
        depth = 0
        quote: str | None = None
        for index in range(start, len(text)):
            char = text[index]
            if quote:
                if char == quote:
                    quote = None
                continue
            if char in {'"', "'", "`"}:
                quote = char
            elif char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
                if depth == 0:
                    return index
        raise DDLImportError("Parenthèse fermante manquante dans CREATE TABLE.")

    @staticmethod
    def _identifier(value: str) -> str:
        value = value.strip()
        if "." in value:
            value = value.rsplit(".", 1)[-1]
        if len(value) >= 2 and (
            (value[0], value[-1]) in {('"', '"'), ("`", "`"), ("[", "]")}
        ):
            value = value[1:-1]
        if not value:
            raise DDLImportError("Identifiant SQL vide.")
        return value.replace('""', '"').replace("``", "`")

    @staticmethod
    def _take_identifier(text: str) -> tuple[str, str]:
        stripped = text.lstrip()
        if stripped[0] in {'"', "`", "["}:
            closing = "]" if stripped[0] == "[" else stripped[0]
            end = stripped.find(closing, 1)
            if end < 0:
                raise DDLImportError("Identifiant SQL cité non fermé.")
            return stripped[: end + 1], stripped[end + 1 :]
        match = re.match(r"[^\s]+", stripped)
        if match is None:
            raise DDLImportError("Nom de colonne manquant.")
        return match.group(0), stripped[match.end() :]

    @staticmethod
    def _strip_constraint_name(part: str) -> tuple[str | None, str]:
        match = re.match(r"(?is)^CONSTRAINT\s+([^\s]+)\s+(.+)$", part.strip())
        if match is None:
            return None, part
        return SQLDDLImporter._identifier(match.group(1)), match.group(2)

    @staticmethod
    def _parenthesized_content(text: str) -> str:
        start = text.find("(")
        if start < 0:
            raise DDLImportError("Contrainte SQL sans liste de colonnes.")
        end = SQLDDLImporter._matching_parenthesis(text, start)
        return text[start + 1 : end].strip()

    @classmethod
    def _parenthesized_names(cls, text: str) -> tuple[str, ...]:
        return tuple(
            cls._identifier(item)
            for item in cls._split_top_level(cls._parenthesized_content(text), ",")
        )

    @classmethod
    def _foreign_key_spec(
        cls, core: str, name: str | None
    ) -> tuple[
        tuple[str, ...],
        str,
        tuple[str, ...],
        str | None,
        MLDReferentialAction | None,
        MLDReferentialAction | None,
    ]:
        match = re.match(
            r"(?is)^FOREIGN\s+KEY\s*\(([^)]*)\)\s+REFERENCES\s+([^\s(]+)\s*\(([^)]*)\)",
            core.strip(),
        )
        if match is None:
            raise DDLImportError("Contrainte FOREIGN KEY invalide.")
        on_delete, on_update = cls._referential_actions(core)
        return (
            tuple(
                cls._identifier(item)
                for item in cls._split_top_level(match.group(1), ",")
            ),
            cls._identifier(match.group(2)),
            tuple(
                cls._identifier(item)
                for item in cls._split_top_level(match.group(3), ",")
            ),
            name,
            on_delete,
            on_update,
        )

    @staticmethod
    def _referential_actions(
        text: str,
    ) -> tuple[MLDReferentialAction | None, MLDReferentialAction | None]:
        def action(kind: str) -> MLDReferentialAction | None:
            match = re.search(
                rf"(?is)\bON\s+{kind}\s+(CASCADE|SET\s+NULL|RESTRICT|NO\s+ACTION|SET\s+DEFAULT)",
                text,
            )
            if match is None:
                return None
            return MLDReferentialAction(re.sub(r"\s+", " ", match.group(1).upper()))

        return action("DELETE"), action("UPDATE")

    @staticmethod
    def _column_ids(
        table: MLDTable, names: tuple[str, ...], kind: str
    ) -> tuple[str, ...]:
        by_name = {column.name.casefold(): column.id for column in table.columns}
        try:
            return tuple(by_name[name.casefold()] for name in names)
        except KeyError as error:
            raise DDLImportError(
                f"La {kind} de {table.name} référence la colonne absente {error.args[0]}."
            ) from error
