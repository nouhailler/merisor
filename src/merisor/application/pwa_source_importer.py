"""Reverse-engineering local d'un projet PWA IndexedDB vers un MCD proposé."""

from __future__ import annotations

import re
import unicodedata
import zipfile
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path, PurePosixPath

from merisor.domain import (
    Association,
    Attribute,
    Cardinality,
    Entity,
    MCDModel,
    MLDDataType,
    MLDDataTypeName,
    Relation,
)
from merisor.domain.validation import ValidationReport, validate_mcd


class PwaImportError(ValueError):
    """La source ne peut pas être analysée de manière sûre."""


class InferenceConfidence(str, Enum):
    CERTAIN = "certain"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

    @property
    def display_name(self) -> str:
        return {
            InferenceConfidence.CERTAIN: "preuve directe",
            InferenceConfidence.HIGH: "confiance élevée",
            InferenceConfidence.MEDIUM: "confiance moyenne",
            InferenceConfidence.LOW: "à confirmer",
        }[self]


@dataclass(frozen=True, slots=True)
class SourceEvidence:
    path: str
    line: int
    message: str
    confidence: InferenceConfidence


@dataclass(frozen=True, slots=True)
class PwaImportResult:
    mcd: MCDModel
    evidence: tuple[SourceEvidence, ...]
    warnings: tuple[str, ...]
    validation: ValidationReport
    scanned_files: int
    database_names: tuple[str, ...]


@dataclass(slots=True)
class _FieldDefinition:
    name: str
    identifier: bool = False
    auto_increment: bool = False
    unique: bool = False
    indexed: bool = False
    nullable: bool | None = None
    data_type: MLDDataType | None = None
    source_path: str = ""
    source_line: int = 1


@dataclass(slots=True)
class _StoreDefinition:
    name: str
    fields: dict[str, _FieldDefinition] = field(default_factory=dict)
    source_path: str = ""
    source_line: int = 1
    version: float = 0.0

    def merge_field(self, candidate: _FieldDefinition) -> None:
        key = _normalized_identifier(candidate.name)
        current = self.fields.get(key)
        if current is None:
            self.fields[key] = candidate
            return
        current.identifier = current.identifier or candidate.identifier
        current.auto_increment = current.auto_increment or candidate.auto_increment
        current.unique = current.unique or candidate.unique
        current.indexed = current.indexed or candidate.indexed
        if candidate.nullable is not None:
            current.nullable = candidate.nullable
        if candidate.data_type is not None and not current.auto_increment:
            current.data_type = candidate.data_type


@dataclass(frozen=True, slots=True)
class _SourceFile:
    path: str
    text: str


class PwaSourceImporter:
    """Analyse statiquement Dexie, IndexedDB natif et les types TypeScript."""

    ALLOWED_SUFFIXES = frozenset(
        {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".json"}
    )
    IGNORED_PARTS = frozenset(
        {
            ".git",
            ".next",
            ".nuxt",
            ".output",
            "build",
            "coverage",
            "dist",
            "node_modules",
            "vendor",
        }
    )
    MAX_FILES = 5_000
    MAX_FILE_BYTES = 2_000_000
    MAX_TOTAL_BYTES = 30_000_000
    SELF_REFERENCE_ROLES = frozenset(
        {"manager", "parent", "responsable", "superviseur", "supervisor"}
    )

    _DEXIE_DATABASE_RE = re.compile(
        r"new\s+Dexie\s*\(\s*['\"](?P<name>[^'\"]+)['\"]\s*\)", re.I
    )
    _IDB_DATABASE_RE = re.compile(
        r"indexedDB\.open\s*\(\s*['\"](?P<name>[^'\"]+)['\"]", re.I
    )
    _DEXIE_STORES_RE = re.compile(
        r"(?:\.version\s*\(\s*(?P<version>[0-9.]+)\s*\)\s*)?"
        r"\.stores\s*\(\s*\{(?P<body>.*?)\}\s*\)",
        re.I | re.S,
    )
    _SCHEMA_ENTRY_RE = re.compile(
        r"(?:['\"](?P<quoted>[^'\"]+)['\"]|(?P<bare>[A-Za-z_$][\w$-]*))"
        r"\s*:\s*['\"](?P<schema>[^'\"]*)['\"]",
        re.S,
    )
    _NATIVE_STORE_RE = re.compile(
        r"(?:(?:const|let|var)\s+)?(?:(?P<variable>[A-Za-z_$][\w$]*)\s*=\s*)?"
        r"[^;\n]*?createObjectStore\s*\(\s*['\"](?P<name>[^'\"]+)['\"]"
        r"(?P<options>\s*,\s*\{.*?\})?\s*\)",
        re.I | re.S,
    )
    _INDEX_RE = re.compile(
        r"(?P<variable>[A-Za-z_$][\w$]*)\.createIndex\s*\(\s*"
        r"['\"](?P<index>[^'\"]+)['\"]\s*,\s*"
        r"(?:['\"](?P<field>[^'\"]+)['\"]|\[(?P<fields>.*?)\])"
        r"(?P<options>\s*,\s*\{.*?\})?\s*\)",
        re.I | re.S,
    )
    _INTERFACE_RE = re.compile(
        r"(?:export\s+)?interface\s+(?P<name>[A-Za-z_$][\w$]*)"
        r"(?:\s+extends[^\{]+)?\s*\{(?P<body>.*?)\}",
        re.S,
    )
    _TYPE_OBJECT_RE = re.compile(
        r"(?:export\s+)?type\s+(?P<name>[A-Za-z_$][\w$]*)\s*=\s*"
        r"\{(?P<body>.*?)\}\s*;",
        re.S,
    )
    _TS_FIELD_RE = re.compile(
        r"(?:readonly\s+)?(?P<name>[A-Za-z_$][\w$]*|['\"][^'\"]+['\"])"
        r"(?P<optional>\?)?\s*:\s*(?P<type>[^;\n,}]+)",
    )

    def import_path(self, source: str | Path) -> PwaImportResult:
        path = Path(source)
        if not path.exists():
            raise PwaImportError(f"La source n'existe pas : {path}")
        files = (
            self._read_archive(path) if path.is_file() else self._read_directory(path)
        )
        if not files:
            raise PwaImportError(
                "Aucun fichier JavaScript, TypeScript ou JSON exploitable trouvé."
            )

        stores: dict[str, _StoreDefinition] = {}
        evidence: list[SourceEvidence] = []
        database_names: set[str] = set()
        type_definitions: dict[str, list[_FieldDefinition]] = {}
        for source_file in files:
            database_names.update(self._database_names(source_file.text))
            self._parse_dexie(source_file, stores, evidence)
            self._parse_native_indexeddb(source_file, stores, evidence)
            self._parse_typescript(source_file, type_definitions, evidence)

        if not stores:
            raise PwaImportError(
                "Aucun object store IndexedDB ni schéma Dexie n'a été détecté."
            )
        self._enrich_from_types(stores, type_definitions, evidence)
        model, warnings = self._to_mcd(stores, evidence)
        return PwaImportResult(
            mcd=model,
            evidence=tuple(evidence),
            warnings=tuple(warnings),
            validation=validate_mcd(model),
            scanned_files=len(files),
            database_names=tuple(sorted(database_names, key=str.casefold)),
        )

    def _read_directory(self, root: Path) -> list[_SourceFile]:
        files: list[_SourceFile] = []
        total = 0
        for path in sorted(root.rglob("*")):
            relative = path.relative_to(root)
            if any(part in self.IGNORED_PARTS for part in relative.parts):
                continue
            if (
                not path.is_file()
                or path.suffix.casefold() not in self.ALLOWED_SUFFIXES
            ):
                continue
            size = path.stat().st_size
            if size > self.MAX_FILE_BYTES:
                continue
            total += size
            self._check_limits(len(files) + 1, total)
            text = self._decode(path.read_bytes())
            if text is not None:
                files.append(_SourceFile(relative.as_posix(), text))
        return files

    def _read_archive(self, archive: Path) -> list[_SourceFile]:
        if archive.suffix.casefold() != ".zip":
            raise PwaImportError("Seuls les dossiers et archives ZIP sont acceptés.")
        files: list[_SourceFile] = []
        total = 0
        try:
            with zipfile.ZipFile(archive) as source_zip:
                for item in sorted(
                    source_zip.infolist(), key=lambda value: value.filename
                ):
                    path = PurePosixPath(item.filename)
                    if item.is_dir() or any(
                        part in self.IGNORED_PARTS for part in path.parts
                    ):
                        continue
                    if path.suffix.casefold() not in self.ALLOWED_SUFFIXES:
                        continue
                    if item.file_size > self.MAX_FILE_BYTES:
                        continue
                    total += item.file_size
                    self._check_limits(len(files) + 1, total)
                    text = self._decode(source_zip.read(item))
                    if text is not None:
                        files.append(_SourceFile(path.as_posix(), text))
        except (OSError, zipfile.BadZipFile) as error:
            raise PwaImportError(f"Archive ZIP illisible : {error}") from error
        return files

    def _parse_dexie(
        self,
        source: _SourceFile,
        stores: dict[str, _StoreDefinition],
        evidence: list[SourceEvidence],
    ) -> None:
        for block in self._DEXIE_STORES_RE.finditer(source.text):
            version = float(block.group("version") or 0)
            for entry in self._SCHEMA_ENTRY_RE.finditer(block.group("body")):
                name = entry.group("quoted") or entry.group("bare")
                schema = entry.group("schema")
                store = self._store(stores, name, source, block.start(), version)
                tokens = [item.strip() for item in schema.split(",") if item.strip()]
                for index, token in enumerate(tokens):
                    self._parse_dexie_token(
                        store, token, index == 0, source, block.start()
                    )
                evidence.append(
                    self._evidence(
                        source,
                        block.start(),
                        f'Schéma Dexie direct détecté pour le store "{name}".',
                        InferenceConfidence.CERTAIN,
                    )
                )

    def _parse_dexie_token(
        self,
        store: _StoreDefinition,
        token: str,
        first: bool,
        source: _SourceFile,
        offset: int,
    ) -> None:
        auto_increment = token.startswith("++")
        unique = token.startswith("&") or "&" in token[:2]
        cleaned = token.lstrip("+&*")
        compound = cleaned.startswith("[") and cleaned.endswith("]")
        names = cleaned[1:-1].split("+") if compound else [cleaned]
        for name in names:
            clean_name = name.strip()
            if not clean_name:
                continue
            store.merge_field(
                _FieldDefinition(
                    clean_name,
                    identifier=first,
                    auto_increment=auto_increment,
                    unique=unique,
                    indexed=True,
                    nullable=None,
                    data_type=(
                        MLDDataType(MLDDataTypeName.INTEGER) if auto_increment else None
                    ),
                    source_path=source.path,
                    source_line=self._line(source.text, offset),
                )
            )

    def _parse_native_indexeddb(
        self,
        source: _SourceFile,
        stores: dict[str, _StoreDefinition],
        evidence: list[SourceEvidence],
    ) -> None:
        variables: dict[str, _StoreDefinition] = {}
        file_stores: list[_StoreDefinition] = []
        for match in self._NATIVE_STORE_RE.finditer(source.text):
            store = self._store(stores, match.group("name"), source, match.start(), 0)
            options = match.group("options") or ""
            key_path_match = re.search(
                r"keyPath\s*:\s*['\"]([^'\"]+)['\"]", options, re.I
            )
            if key_path_match:
                auto_increment = bool(
                    re.search(r"autoIncrement\s*:\s*true", options, re.I)
                )
                store.merge_field(
                    _FieldDefinition(
                        key_path_match.group(1),
                        identifier=True,
                        auto_increment=auto_increment,
                        indexed=True,
                        data_type=(
                            MLDDataType(MLDDataTypeName.INTEGER)
                            if auto_increment
                            else None
                        ),
                        source_path=source.path,
                        source_line=self._line(source.text, match.start()),
                    )
                )
            if match.group("variable"):
                variables[match.group("variable")] = store
            file_stores.append(store)
            evidence.append(
                self._evidence(
                    source,
                    match.start(),
                    f'Appel createObjectStore direct détecté pour "{store.name}".',
                    InferenceConfidence.CERTAIN,
                )
            )
        for match in self._INDEX_RE.finditer(source.text):
            index_store = variables.get(match.group("variable"))
            if index_store is None and len({item.name for item in file_stores}) == 1:
                index_store = file_stores[0]
            if index_store is None:
                continue
            names = re.findall(r"['\"]([^'\"]+)['\"]", match.group("fields") or "")
            if not names and match.group("field"):
                names = [match.group("field")]
            for name in names:
                index_store.merge_field(
                    _FieldDefinition(
                        name,
                        unique=bool(
                            re.search(
                                r"unique\s*:\s*true", match.group("options") or "", re.I
                            )
                        ),
                        indexed=True,
                        source_path=source.path,
                        source_line=self._line(source.text, match.start()),
                    )
                )

    def _parse_typescript(
        self,
        source: _SourceFile,
        definitions: dict[str, list[_FieldDefinition]],
        evidence: list[SourceEvidence],
    ) -> None:
        if Path(source.path).suffix.casefold() not in {".ts", ".tsx"}:
            return
        for pattern in (self._INTERFACE_RE, self._TYPE_OBJECT_RE):
            for match in pattern.finditer(source.text):
                fields: list[_FieldDefinition] = []
                for field_match in self._TS_FIELD_RE.finditer(match.group("body")):
                    name = field_match.group("name").strip("'\"")
                    fields.append(
                        _FieldDefinition(
                            name,
                            nullable=bool(field_match.group("optional"))
                            or "undefined" in field_match.group("type")
                            or "null" in field_match.group("type"),
                            data_type=self._typescript_type(field_match.group("type")),
                            source_path=source.path,
                            source_line=self._line(source.text, match.start()),
                        )
                    )
                if fields:
                    definitions.setdefault(
                        _normalized_identifier(match.group("name")), []
                    ).extend(fields)
                    evidence.append(
                        self._evidence(
                            source,
                            match.start(),
                            f"Type TypeScript {match.group('name')} utilisé pour "
                            "enrichir les attributs proposés.",
                            InferenceConfidence.MEDIUM,
                        )
                    )

    def _enrich_from_types(
        self,
        stores: dict[str, _StoreDefinition],
        definitions: dict[str, list[_FieldDefinition]],
        evidence: list[SourceEvidence],
    ) -> None:
        del evidence
        for store in stores.values():
            key = _normalized_identifier(_singularize(store.name))
            candidates = definitions.get(key, [])
            if not candidates:
                candidates = definitions.get(key + "record", []) or definitions.get(
                    key + "model", []
                )
            for field_definition in candidates:
                store.merge_field(field_definition)

    def _to_mcd(
        self,
        stores: dict[str, _StoreDefinition],
        evidence: list[SourceEvidence],
    ) -> tuple[MCDModel, list[str]]:
        model = MCDModel()
        warnings: list[str] = []
        entity_by_store: dict[str, Entity] = {}
        attribute_by_store: dict[str, dict[str, Attribute]] = {}
        for store in sorted(stores.values(), key=lambda item: item.name.casefold()):
            entity_name = _singularize(store.name).upper()
            fields = list(store.fields.values())
            if not any(item.identifier for item in fields):
                likely_id = next(
                    (
                        item
                        for item in fields
                        if _normalized_identifier(item.name) == "id"
                    ),
                    None,
                )
                if likely_id is not None:
                    likely_id.identifier = True
                    evidence.append(
                        SourceEvidence(
                            likely_id.source_path,
                            likely_id.source_line,
                            f"{store.name}.id proposé comme identifiant.",
                            InferenceConfidence.MEDIUM,
                        )
                    )
                else:
                    technical_name = f"id_{_safe_name(_singularize(store.name))}"
                    fields.insert(
                        0,
                        _FieldDefinition(
                            technical_name,
                            identifier=True,
                            auto_increment=True,
                            nullable=False,
                            data_type=MLDDataType(MLDDataTypeName.INTEGER),
                            source_path=store.source_path,
                            source_line=store.source_line,
                        ),
                    )
                    message = (
                        f"{entity_name} : aucun keyPath détecté ; l'identifiant "
                        f"technique {technical_name} est proposé et doit être confirmé."
                    )
                    warnings.append(message)
                    evidence.append(
                        SourceEvidence(
                            store.source_path,
                            store.source_line,
                            message,
                            InferenceConfidence.LOW,
                        )
                    )
            attributes = [
                Attribute(
                    item.name,
                    identifier=item.identifier,
                    id=f"pwa:attribute:{_safe_name(store.name)}:{_safe_name(item.name)}",
                    data_type=item.data_type,
                    nullable=False if item.identifier else item.nullable,
                    unique=item.unique,
                    auto_increment=item.auto_increment,
                )
                for item in fields
            ]
            entity = Entity(
                entity_name,
                id=f"pwa:entity:{_safe_name(store.name)}",
                attributes=attributes,
            )
            model.add_entity(entity)
            store_key = _normalized_identifier(_singularize(store.name))
            entity_by_store[store_key] = entity
            attribute_by_store[store_key] = {
                _normalized_identifier(item.name): attribute
                for item, attribute in zip(fields, attributes, strict=True)
            }

        for child_key, child in sorted(entity_by_store.items()):
            store = next(
                item
                for item in stores.values()
                if _normalized_identifier(_singularize(item.name)) == child_key
            )
            for field_definition in store.fields.values():
                attribute = attribute_by_store[child_key].get(
                    _normalized_identifier(field_definition.name)
                )
                if attribute is None or attribute.identifier:
                    continue
                target_key = self._foreign_target(
                    field_definition.name, entity_by_store, child_key
                )
                if target_key is None:
                    continue
                target = entity_by_store[target_key]
                association_id = (
                    f"pwa:association:{child_key}:"
                    f"{_safe_name(field_definition.name)}:{target_key}"
                )
                association = Association(
                    f"REFERENCER_{child.name}_{target.name}_"
                    f"{field_definition.name.upper()}",
                    id=association_id,
                )
                model.add_association(association)
                reflexive = child.id == target.id
                model.add_relation(
                    Relation(
                        target.id,
                        association.id,
                        id=f"pwa:relation:{association_id}:referenced",
                        cardinality=Cardinality("0", "N"),
                        role=(
                            f"référencé_{field_definition.name}" if reflexive else ""
                        ),
                    )
                )
                model.add_relation(
                    Relation(
                        child.id,
                        association.id,
                        id=f"pwa:relation:{association_id}:carrier",
                        cardinality=Cardinality(
                            "0" if field_definition.nullable is not False else "1",
                            "1",
                        ),
                        role=(f"porteur_{field_definition.name}" if reflexive else ""),
                    )
                )
                confidence = (
                    InferenceConfidence.HIGH
                    if field_definition.indexed
                    else InferenceConfidence.MEDIUM
                )
                evidence.append(
                    SourceEvidence(
                        field_definition.source_path,
                        field_definition.source_line,
                        f"Relation proposée : {child.name}.{field_definition.name} "
                        f"→ {target.name}.",
                        confidence,
                    )
                )
        return model, warnings

    @staticmethod
    def _store(
        stores: dict[str, _StoreDefinition],
        name: str,
        source: _SourceFile,
        offset: int,
        version: float,
    ) -> _StoreDefinition:
        key = _normalized_identifier(name)
        store = stores.get(key)
        if store is None:
            store = _StoreDefinition(
                name,
                source_path=source.path,
                source_line=PwaSourceImporter._line(source.text, offset),
                version=version,
            )
            stores[key] = store
        elif version >= store.version:
            store.version = version
        return store

    @staticmethod
    def _database_names(text: str) -> set[str]:
        return {
            match.group("name")
            for pattern in (
                PwaSourceImporter._DEXIE_DATABASE_RE,
                PwaSourceImporter._IDB_DATABASE_RE,
            )
            for match in pattern.finditer(text)
        }

    @staticmethod
    def _foreign_target(
        field_name: str, entities: dict[str, Entity], current_entity_key: str
    ) -> str | None:
        words = _split_identifier(field_name)
        candidates: list[str] = []
        if words and words[-1] in {"id", "key", "uuid"}:
            candidates.append("".join(words[:-1]))
        if words and words[0] == "id":
            candidates.append("".join(words[1:]))
        for candidate in candidates:
            normalized = _normalized_identifier(_singularize(candidate))
            if normalized in entities:
                return normalized
        if words and words[0] in PwaSourceImporter.SELF_REFERENCE_ROLES:
            return current_entity_key
        return None

    @staticmethod
    def _typescript_type(value: str) -> MLDDataType:
        normalized = value.casefold().replace(" ", "")
        if "boolean" in normalized:
            return MLDDataType(MLDDataTypeName.BOOLEAN)
        if "date" in normalized:
            return MLDDataType(MLDDataTypeName.DATETIME)
        if "number" in normalized or "bigint" in normalized:
            return MLDDataType(
                MLDDataTypeName.BIGINT
                if "bigint" in normalized
                else MLDDataTypeName.INTEGER
            )
        if "string" in normalized:
            return MLDDataType.varchar(255)
        return MLDDataType(MLDDataTypeName.TEXT)

    @staticmethod
    def _evidence(
        source: _SourceFile,
        offset: int,
        message: str,
        confidence: InferenceConfidence,
    ) -> SourceEvidence:
        return SourceEvidence(
            source.path,
            PwaSourceImporter._line(source.text, offset),
            message,
            confidence,
        )

    @staticmethod
    def _line(text: str, offset: int) -> int:
        return text.count("\n", 0, offset) + 1

    @staticmethod
    def _decode(content: bytes) -> str | None:
        if b"\x00" in content[:1024]:
            return None
        try:
            return content.decode("utf-8")
        except UnicodeDecodeError:
            return None

    def _check_limits(self, file_count: int, total_bytes: int) -> None:
        if file_count > self.MAX_FILES:
            raise PwaImportError(
                f"Le projet dépasse la limite de {self.MAX_FILES} fichiers analysables."
            )
        if total_bytes > self.MAX_TOTAL_BYTES:
            raise PwaImportError(
                "Le volume de sources analysables dépasse la limite de 30 Mo."
            )


def _split_identifier(value: str) -> list[str]:
    with_spaces = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    return [
        item for item in re.split(r"[^0-9A-Za-zÀ-ÿ]+", with_spaces.casefold()) if item
    ]


def _normalized_identifier(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    return "".join(
        character
        for character in decomposed
        if not unicodedata.combining(character) and character.isalnum()
    )


def _singularize(value: str) -> str:
    words = _split_identifier(value)
    if not words:
        return value
    last = words[-1]
    if last.endswith("ies") and len(last) > 3:
        last = last[:-3] + "y"
    elif last.endswith("aux") and len(last) > 4:
        last = last[:-3] + "al"
    elif last.endswith("s") and not last.endswith("ss") and len(last) > 2:
        last = last[:-1]
    return "_".join((*words[:-1], last))


def _safe_name(value: str) -> str:
    return _normalized_identifier(value) or "element"
