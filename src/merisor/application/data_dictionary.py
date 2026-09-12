"""Projection consultable du dictionnaire de données porté par le MCD."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from merisor.domain import Association, Attribute, BusinessTerm, Entity, MCDModel


class DictionaryEntryKind(str, Enum):
    ENTITY = "entity"
    ASSOCIATION = "association"
    ATTRIBUTE = "attribute"
    BUSINESS_TERM = "business_term"

    @property
    def label(self) -> str:
        return {
            DictionaryEntryKind.ENTITY: "Entité",
            DictionaryEntryKind.ASSOCIATION: "Association",
            DictionaryEntryKind.ATTRIBUTE: "Attribut",
            DictionaryEntryKind.BUSINESS_TERM: "Terme métier",
        }[self]


@dataclass(frozen=True, slots=True)
class DataDictionaryEntry:
    id: str
    name: str
    kind: DictionaryEntryKind
    description: str
    owner_name: str = ""
    type_label: str = ""
    role: str = ""
    nullable: str = ""
    unique: bool = False
    synonyms: tuple[str, ...] = ()

    def render(self) -> str:
        lines = [self.name, "", f"Nature : {self.kind.label}"]
        if self.owner_name:
            lines.append(f"Propriétaire : {self.owner_name}")
        lines.extend(("", "Description :", self.description or "Non renseignée."))
        if self.type_label:
            lines.extend(
                (
                    "",
                    f"Type logique : {self.type_label}",
                    f"Rôle : {self.role}",
                    f"Nullable : {self.nullable}",
                    f"Unique : {'oui' if self.unique else 'non'}",
                )
            )
        if self.synonyms:
            lines.extend(("", "Synonymes : " + ", ".join(self.synonyms)))
        return "\n".join(lines)


@dataclass(frozen=True, slots=True)
class DataDictionary:
    entries: tuple[DataDictionaryEntry, ...]

    def render(self) -> str:
        return "\n\n".join(entry.render() for entry in self.entries)


class DataDictionaryService:
    """Construit le dictionnaire depuis les données explicites, sans les inventer."""

    def build(self, model: MCDModel) -> DataDictionary:
        entries: list[DataDictionaryEntry] = []
        nodes: tuple[Entity | Association, ...] = (
            *model.entities.values(),
            *model.associations.values(),
        )
        for node in sorted(nodes, key=lambda item: (item.name.casefold(), item.id)):
            kind = (
                DictionaryEntryKind.ENTITY
                if isinstance(node, Entity)
                else DictionaryEntryKind.ASSOCIATION
            )
            entries.append(
                DataDictionaryEntry(
                    node.id,
                    node.name,
                    kind,
                    node.description,
                )
            )
            entries.extend(
                self._attribute_entry(node.name, attribute)
                for attribute in node.attributes
            )
        entries.extend(
            self._term_entry(term)
            for term in sorted(
                model.business_terms.values(),
                key=lambda item: (item.name.casefold(), item.id),
            )
        )
        return DataDictionary(tuple(entries))

    @staticmethod
    def _attribute_entry(owner_name: str, attribute: Attribute) -> DataDictionaryEntry:
        if attribute.data_type is not None:
            type_label = attribute.data_type.label
        else:
            inferred = "INTEGER" if attribute.identifier else "VARCHAR(100)"
            type_label = f"Automatique ({inferred})"
        nullable = (
            "automatique"
            if attribute.nullable is None
            else "oui"
            if attribute.nullable
            else "non"
        )
        return DataDictionaryEntry(
            attribute.id,
            attribute.name,
            DictionaryEntryKind.ATTRIBUTE,
            attribute.comment,
            owner_name=owner_name,
            type_label=type_label,
            role="identifiant" if attribute.identifier else "donnée métier",
            nullable=nullable,
            unique=attribute.unique,
        )

    @staticmethod
    def _term_entry(term: BusinessTerm) -> DataDictionaryEntry:
        return DataDictionaryEntry(
            term.id,
            term.name,
            DictionaryEntryKind.BUSINESS_TERM,
            term.definition,
            synonyms=term.synonyms,
        )
