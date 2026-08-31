"""Modèle logique de données indépendant du MCD et de toute interface."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class MLDError(ValueError):
    """Incohérence structurelle d'un modèle logique de données."""


class MLDTableSource(str, Enum):
    ENTITY = "entity"
    ASSOCIATION = "association"


class MLDDataTypeName(str, Enum):
    """Types logiques indépendants de tout dialecte SQL."""

    INTEGER = "INTEGER"
    BIGINT = "BIGINT"
    DECIMAL = "DECIMAL"
    FLOAT = "FLOAT"
    BOOLEAN = "BOOLEAN"
    VARCHAR = "VARCHAR"
    TEXT = "TEXT"
    DATE = "DATE"
    TIME = "TIME"
    DATETIME = "DATETIME"
    TIMESTAMP = "TIMESTAMP"


class MLDReferentialAction(str, Enum):
    CASCADE = "CASCADE"
    SET_NULL = "SET NULL"
    RESTRICT = "RESTRICT"
    NO_ACTION = "NO ACTION"
    SET_DEFAULT = "SET DEFAULT"


def _require_identifier(value: str, kind: str) -> None:
    if not isinstance(value, str) or not value:
        raise MLDError(f"L'identifiant de {kind} est obligatoire.")


@dataclass(frozen=True, slots=True)
class MLDDataType:
    """Type logique paramétrable traduit ensuite par un dialecte SQL."""

    name: MLDDataTypeName | str
    length: int | None = None
    precision: int | None = None
    scale: int | None = None

    def __post_init__(self) -> None:
        try:
            name = MLDDataTypeName(self.name)
        except (TypeError, ValueError) as error:
            raise MLDError(f"Type logique inconnu : {self.name!r}.") from error
        object.__setattr__(self, "name", name)
        if name is MLDDataTypeName.VARCHAR:
            if not isinstance(self.length, int) or self.length <= 0:
                raise MLDError("VARCHAR exige une longueur entière positive.")
        elif self.length is not None:
            raise MLDError("Seul VARCHAR accepte une longueur.")
        if name is MLDDataTypeName.DECIMAL:
            if self.precision is not None and (
                not isinstance(self.precision, int) or self.precision <= 0
            ):
                raise MLDError("La précision DECIMAL doit être positive.")
            if self.scale is not None and (
                self.precision is None
                or not isinstance(self.scale, int)
                or self.scale < 0
                or self.scale > self.precision
            ):
                raise MLDError("L'échelle DECIMAL doit être comprise dans la précision.")
        elif self.precision is not None or self.scale is not None:
            raise MLDError("Seul DECIMAL accepte précision et échelle.")

    @classmethod
    def varchar(cls, length: int = 100) -> MLDDataType:
        return cls(MLDDataTypeName.VARCHAR, length=length)

    @property
    def label(self) -> str:
        if self.name is MLDDataTypeName.VARCHAR:
            return f"VARCHAR({self.length})"
        if self.name is MLDDataTypeName.DECIMAL and self.precision is not None:
            if self.scale is None:
                return f"DECIMAL({self.precision})"
            return f"DECIMAL({self.precision},{self.scale})"
        return self.name.value


def _default_data_type() -> MLDDataType:
    return MLDDataType.varchar(100)


@dataclass(frozen=True, slots=True)
class MLDColumn:
    """Colonne logique, native ou migrée depuis une autre table."""

    id: str
    name: str
    nullable: bool | None
    data_type: MLDDataType = field(default_factory=_default_data_type)
    default: str | None = None
    source_attribute_id: str | None = None
    source_element_id: str | None = None
    source_relation_id: str | None = None
    generated: bool = False
    auto_increment: bool = False

    def __post_init__(self) -> None:
        _require_identifier(self.id, "la colonne")
        if not isinstance(self.name, str) or not self.name:
            raise MLDError("Le nom d'une colonne est obligatoire.")
        if self.nullable is not None and not isinstance(self.nullable, bool):
            raise MLDError("La nullabilité doit être booléenne ou inconnue.")
        if not isinstance(self.data_type, MLDDataType):
            raise MLDError("Le type logique d'une colonne est invalide.")
        if self.default is not None and not isinstance(self.default, str):
            raise MLDError("La valeur par défaut logique doit être textuelle.")
        if not isinstance(self.generated, bool) or not isinstance(
            self.auto_increment, bool
        ):
            raise MLDError("Les indicateurs de génération doivent être booléens.")


def _normalize_action(
    action: MLDReferentialAction | str | None,
) -> MLDReferentialAction | None:
    if action is None:
        return None
    try:
        return MLDReferentialAction(action)
    except (TypeError, ValueError) as error:
        raise MLDError(f"Action référentielle inconnue : {action!r}.") from error


@dataclass(frozen=True, slots=True)
class MLDForeignKey:
    """Contrainte FK simple ou composée."""

    id: str
    column_ids: tuple[str, ...]
    referenced_table_id: str
    referenced_column_ids: tuple[str, ...]
    source_association_id: str
    source_relation_id: str | None = None
    source_inheritance_id: str | None = None
    source_cardinality: tuple[str, str] | None = None
    name: str | None = None
    on_delete: MLDReferentialAction | str | None = None
    on_update: MLDReferentialAction | str | None = None

    def __post_init__(self) -> None:
        _require_identifier(self.id, "la clé étrangère")
        _require_identifier(self.referenced_table_id, "la table référencée")
        _require_identifier(self.source_association_id, "l'association source")
        if not self.column_ids or len(self.column_ids) != len(
            self.referenced_column_ids
        ):
            raise MLDError(
                "Une FK doit référencer le même nombre de colonnes locales et distantes."
            )
        if self.source_relation_id is not None:
            _require_identifier(self.source_relation_id, "la relation source")
        if self.source_inheritance_id is not None:
            _require_identifier(self.source_inheritance_id, "l'héritage source")
        if self.source_cardinality is not None and (
            len(self.source_cardinality) != 2
            or self.source_cardinality[0] not in {"0", "1"}
            or self.source_cardinality[1] not in {"1", "N"}
        ):
            raise MLDError("La cardinalité MCD source d'une FK est invalide.")
        if self.name is not None and (not isinstance(self.name, str) or not self.name):
            raise MLDError("Le nom SQL optionnel d'une FK doit être non vide.")
        object.__setattr__(self, "on_delete", _normalize_action(self.on_delete))
        object.__setattr__(self, "on_update", _normalize_action(self.on_update))


@dataclass(frozen=True, slots=True)
class MLDUniqueConstraint:
    """Contrainte d'unicité simple ou composée, notamment pour les 1:1."""

    id: str
    column_ids: tuple[str, ...]
    source_association_id: str
    name: str | None = None

    def __post_init__(self) -> None:
        _require_identifier(self.id, "la contrainte UNIQUE")
        _require_identifier(self.source_association_id, "l'association source")
        if not self.column_ids:
            raise MLDError("Une contrainte UNIQUE doit contenir une colonne.")
        if self.name is not None and (not isinstance(self.name, str) or not self.name):
            raise MLDError("Le nom SQL optionnel d'une contrainte doit être non vide.")


@dataclass(frozen=True, slots=True)
class MLDCheckConstraint:
    id: str
    expression: str
    name: str | None = None
    source_element_id: str | None = None

    def __post_init__(self) -> None:
        _require_identifier(self.id, "la contrainte CHECK")
        if not isinstance(self.expression, str) or not self.expression.strip():
            raise MLDError("L'expression d'une contrainte CHECK est obligatoire.")
        if self.name is not None and (not isinstance(self.name, str) or not self.name):
            raise MLDError("Le nom SQL optionnel d'un CHECK doit être non vide.")


@dataclass(frozen=True, slots=True)
class MLDIndex:
    id: str
    name: str
    column_ids: tuple[str, ...]
    unique: bool = False

    def __post_init__(self) -> None:
        _require_identifier(self.id, "l'index")
        if not isinstance(self.name, str) or not self.name:
            raise MLDError("Le nom d'un index est obligatoire.")
        if not self.column_ids:
            raise MLDError("Un index doit contenir au moins une colonne.")
        if not isinstance(self.unique, bool):
            raise MLDError("Le statut UNIQUE d'un index doit être booléen.")


@dataclass(slots=True)
class MLDTable:
    """Table logique avec contraintes exprimées par identifiants de colonnes."""

    id: str
    name: str
    source_element_id: str
    source: MLDTableSource
    columns: list[MLDColumn] = field(default_factory=list)
    primary_key: tuple[str, ...] = ()
    foreign_keys: list[MLDForeignKey] = field(default_factory=list)
    unique_constraints: list[MLDUniqueConstraint] = field(default_factory=list)
    is_historized: bool = False
    check_constraints: list[MLDCheckConstraint] = field(default_factory=list)
    indexes: list[MLDIndex] = field(default_factory=list)

    def __post_init__(self) -> None:
        _require_identifier(self.id, "la table")
        _require_identifier(self.source_element_id, "l'élément source")
        if not isinstance(self.name, str) or not self.name:
            raise MLDError("Le nom d'une table est obligatoire.")
        if not isinstance(self.is_historized, bool):
            raise MLDError("Le statut d'historisation d'une table doit être booléen.")
        if self.is_historized and self.source is not MLDTableSource.ASSOCIATION:
            raise MLDError(
                "Seule une table issue d'une association peut être historisée."
            )

    def column_by_id(self, column_id: str) -> MLDColumn:
        for column in self.columns:
            if column.id == column_id:
                return column
        raise MLDError(f"Colonne inconnue dans {self.name} : {column_id}")

    def column(self, name: str) -> MLDColumn:
        matches = [column for column in self.columns if column.name == name]
        if len(matches) != 1:
            raise MLDError(
                f"La colonne {name!r} est absente ou ambiguë dans {self.name}."
            )
        return matches[0]

    @property
    def primary_key_columns(self) -> tuple[MLDColumn, ...]:
        return tuple(self.column_by_id(column_id) for column_id in self.primary_key)

    def is_primary_key(self, column_id: str) -> bool:
        return column_id in self.primary_key

    def is_foreign_key(self, column_id: str) -> bool:
        return any(column_id in foreign_key.column_ids for foreign_key in self.foreign_keys)

    def is_unique(self, column_id: str) -> bool:
        return any(
            constraint.column_ids == (column_id,)
            for constraint in self.unique_constraints
        )


@dataclass(slots=True)
class MLDModel:
    """Résultat autonome d'une transformation d'un état logique du MCD."""

    tables: list[MLDTable]
    generated_from_fingerprint: str

    def __post_init__(self) -> None:
        table_ids = [table.id for table in self.tables]
        if len(table_ids) != len(set(table_ids)):
            raise MLDError("Le MLD contient des identifiants de tables dupliqués.")
        tables = {table.id: table for table in self.tables}
        for table in self.tables:
            column_ids = {column.id for column in table.columns}
            if len(column_ids) != len(table.columns):
                raise MLDError(
                    f"La table {table.name} contient des identifiants de colonnes dupliqués."
                )
            if not set(table.primary_key).issubset(column_ids):
                raise MLDError(f"La PK de {table.name} référence une colonne absente.")
            for foreign_key in table.foreign_keys:
                if not set(foreign_key.column_ids).issubset(column_ids):
                    raise MLDError(
                        f"Une FK de {table.name} référence une colonne locale absente."
                    )
                target = tables.get(foreign_key.referenced_table_id)
                if target is None:
                    raise MLDError(
                        f"Une FK de {table.name} référence une table absente."
                    )
                target_ids = {column.id for column in target.columns}
                if not set(foreign_key.referenced_column_ids).issubset(target_ids):
                    raise MLDError(
                        f"Une FK de {table.name} référence une colonne distante absente."
                    )
            for constraint in table.unique_constraints:
                if not set(constraint.column_ids).issubset(column_ids):
                    raise MLDError(
                        f"Une contrainte UNIQUE de {table.name} référence une colonne absente."
                    )
            for index in table.indexes:
                if not set(index.column_ids).issubset(column_ids):
                    raise MLDError(
                        f"Un index de {table.name} référence une colonne absente."
                    )

    def table_by_id(self, table_id: str) -> MLDTable:
        for table in self.tables:
            if table.id == table_id:
                return table
        raise MLDError(f"Table inconnue : {table_id}")

    def table(self, name: str) -> MLDTable:
        matches = [table for table in self.tables if table.name == name]
        if len(matches) != 1:
            raise MLDError(f"La table {name!r} est absente ou ambiguë.")
        return matches[0]
