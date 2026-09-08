"""Tests fonctionnels déterministes appliqués à un MCD sans le modifier."""

from __future__ import annotations

import re
import unicodedata
from collections import deque
from dataclasses import dataclass
from enum import Enum

from merisor.domain import (
    Association,
    CardinalityMaximum,
    Entity,
    MCDModel,
    Relation,
)


class ScenarioCheckStatus(str, Enum):
    SATISFIED = "satisfied"
    RISK = "risk"
    UNVERIFIABLE = "unverifiable"

    @property
    def label(self) -> str:
        return {
            ScenarioCheckStatus.SATISFIED: "Satisfait",
            ScenarioCheckStatus.RISK: "Risque",
            ScenarioCheckStatus.UNVERIFIABLE: "Non vérifiable",
        }[self]


@dataclass(frozen=True, slots=True)
class BusinessScenario:
    title: str
    expectations: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.title.strip():
            raise ValueError("Le scénario doit posséder un titre.")
        if not self.expectations:
            raise ValueError("Le scénario doit contenir au moins une attente métier.")


@dataclass(frozen=True, slots=True)
class ScenarioPathElement:
    element_id: str
    label: str
    kind: str


@dataclass(frozen=True, slots=True)
class ScenarioCheck:
    expectation: str
    status: ScenarioCheckStatus
    explanation: str
    element_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class BusinessScenarioReport:
    scenario: BusinessScenario
    path: tuple[ScenarioPathElement, ...]
    checks: tuple[ScenarioCheck, ...]

    @property
    def satisfied(self) -> tuple[ScenarioCheck, ...]:
        return tuple(
            check
            for check in self.checks
            if check.status is ScenarioCheckStatus.SATISFIED
        )

    @property
    def risks(self) -> tuple[ScenarioCheck, ...]:
        return tuple(
            check for check in self.checks if check.status is ScenarioCheckStatus.RISK
        )

    @property
    def unverifiable(self) -> tuple[ScenarioCheck, ...]:
        return tuple(
            check
            for check in self.checks
            if check.status is ScenarioCheckStatus.UNVERIFIABLE
        )

    def render(self) -> str:
        lines = [f"SCÉNARIO — {self.scenario.title}", "=" * 56, ""]
        if self.path:
            lines.extend(
                ("CHEMIN MÉTIER", " → ".join(item.label for item in self.path))
            )
        else:
            lines.extend(
                (
                    "CHEMIN MÉTIER",
                    "Aucun concept du scénario n'a été reconnu dans le MCD.",
                )
            )
        lines.extend(("", "VÉRIFICATION"))
        icons = {
            ScenarioCheckStatus.SATISFIED: "✓",
            ScenarioCheckStatus.RISK: "⚠",
            ScenarioCheckStatus.UNVERIFIABLE: "?",
        }
        for check in self.checks:
            lines.append(f"{icons[check.status]} {check.expectation}")
            lines.append(f"  {check.explanation}")
        lines.extend(
            (
                "",
                "Ce rapport teste ce que la structure du MCD permet d'établir. ",
                "Il ne prouve pas à lui seul toutes les règles métier.",
            )
        )
        return "\n".join(lines)


def parse_scenario(title: str, text: str) -> BusinessScenario:
    """Transforme une saisie libre en attentes stables, une phrase par contrôle."""

    expectations: list[str] = []
    for line in text.splitlines():
        clean_line = line.strip().lstrip("-•✓⚠ ").strip()
        if not clean_line:
            continue
        expectations.extend(
            sentence.strip()
            for sentence in re.split(r"(?<=[.!?])\s+", clean_line)
            if sentence.strip()
        )
    return BusinessScenario(title.strip(), tuple(expectations))


class BusinessScenarioAnalyzer:
    """Évalue des attentes explicites à partir du graphe et des attributs MCD."""

    def analyze(
        self, model: MCDModel, scenario: BusinessScenario
    ) -> BusinessScenarioReport:
        mentioned = self._mentioned_nodes(
            model, " ".join((scenario.title, *scenario.expectations))
        )
        path = self._combined_path(model, mentioned)
        checks = tuple(
            self._evaluate_expectation(model, expectation)
            for expectation in scenario.expectations
        )
        return BusinessScenarioReport(scenario, path, checks)

    def _evaluate_expectation(self, model: MCDModel, expectation: str) -> ScenarioCheck:
        normalized = _normalized(expectation)
        nodes = self._mentioned_nodes(model, expectation)

        if "disponib" in normalized and any(
            token in normalized for token in ("date", "periode", "moment")
        ):
            return ScenarioCheck(
                expectation,
                ScenarioCheckStatus.UNVERIFIABLE,
                "Le MCD peut stocker des périodes, mais sa seule structure ne prouve "
                "pas l'absence de chevauchement ni la disponibilité à une date. "
                "Cette règle métier doit être documentée ou contrainte séparément.",
                tuple(node.id for node in nodes),
            )

        attribute_check = self._attribute_check(model, expectation, nodes)
        if attribute_check is not None:
            return attribute_check

        if any(token in normalized for token in ("plusieur", "multiple")):
            return self._multiplicity_check(model, expectation, nodes)

        if len(nodes) >= 2:
            path = self._shortest_path(model, nodes[0].id, nodes[1].id)
            if path:
                return ScenarioCheck(
                    expectation,
                    ScenarioCheckStatus.SATISFIED,
                    "Les concepts sont reliés par : "
                    + " → ".join(model.node(item).name for item in path)
                    + ".",
                    tuple(path),
                )
            return ScenarioCheck(
                expectation,
                ScenarioCheckStatus.RISK,
                "Les concepts cités existent, mais aucun chemin ne les relie.",
                tuple(node.id for node in nodes),
            )

        return ScenarioCheck(
            expectation,
            ScenarioCheckStatus.UNVERIFIABLE,
            "Cette attente n'est pas exprimée de manière vérifiable dans la "
            "structure actuelle. Citez les concepts ou l'attribut attendu.",
            tuple(node.id for node in nodes),
        )

    def _attribute_check(
        self,
        model: MCDModel,
        expectation: str,
        nodes: tuple[Entity | Association, ...],
    ) -> ScenarioCheck | None:
        normalized = _normalized(expectation)
        match = re.search(
            r"(?:possede|contient|comprend|avec)_(?:un|une|des|le|la)_([a-z0-9_]+)",
            normalized,
        )
        if match is None or not nodes:
            return None
        requested = match.group(1).strip("_")
        owner = nodes[0]
        attribute = next(
            (
                item
                for item in owner.attributes
                if _concept_matches(_normalized(item.name), requested)
            ),
            None,
        )
        if attribute is not None:
            return ScenarioCheck(
                expectation,
                ScenarioCheckStatus.SATISFIED,
                f"{owner.name}.{attribute.name} représente cette information.",
                (owner.id, attribute.id),
            )
        readable = requested.replace("_", " ")
        return ScenarioCheck(
            expectation,
            ScenarioCheckStatus.RISK,
            f"Aucun attribut de {owner.name} ne correspond à « {readable} ».",
            (owner.id,),
        )

    def _multiplicity_check(
        self,
        model: MCDModel,
        expectation: str,
        nodes: tuple[Entity | Association, ...],
    ) -> ScenarioCheck:
        if len(nodes) < 2:
            return ScenarioCheck(
                expectation,
                ScenarioCheckStatus.UNVERIFIABLE,
                "La vérification d'une multiplicité exige deux concepts reconnus.",
                tuple(node.id for node in nodes),
            )
        path = self._shortest_path(model, nodes[0].id, nodes[1].id)
        if len(path) < 2:
            return ScenarioCheck(
                expectation,
                ScenarioCheckStatus.RISK,
                "Aucun chemin MCD ne relie les deux concepts cités.",
                tuple(node.id for node in nodes),
            )
        first_relation = self._relation_between(model, path[0], path[1])
        if (
            first_relation is not None
            and first_relation.cardinality is not None
            and first_relation.cardinality.maximum is CardinalityMaximum.MANY
        ):
            return ScenarioCheck(
                expectation,
                ScenarioCheckStatus.SATISFIED,
                f"La branche de {nodes[0].name} porte la cardinalité "
                f"{first_relation.cardinality}.",
                tuple(path),
            )
        cardinality = (
            str(first_relation.cardinality)
            if first_relation is not None and first_relation.cardinality is not None
            else "inconnue"
        )
        return ScenarioCheck(
            expectation,
            ScenarioCheckStatus.RISK,
            f"La branche de {nodes[0].name} ne permet pas plusieurs occurrences "
            f"(cardinalité {cardinality}).",
            tuple(path),
        )

    def _combined_path(
        self, model: MCDModel, nodes: tuple[Entity | Association, ...]
    ) -> tuple[ScenarioPathElement, ...]:
        if not nodes:
            return ()
        ids = [nodes[0].id]
        for target in nodes[1:]:
            segment = self._shortest_path(model, ids[-1], target.id)
            if segment:
                ids.extend(segment[1:])
        return tuple(
            ScenarioPathElement(
                element_id,
                model.node(element_id).name,
                "Entité" if element_id in model.entities else "Association",
            )
            for element_id in dict.fromkeys(ids)
        )

    def _mentioned_nodes(
        self, model: MCDModel, text: str
    ) -> tuple[Entity | Association, ...]:
        normalized = _normalized(text)
        words = normalized.split("_")
        positions: list[tuple[int, int, Entity | Association]] = []
        nodes: tuple[Entity | Association, ...] = (
            *model.entities.values(),
            *model.associations.values(),
        )
        for node in nodes:
            node_words = _normalized(node.name).split("_")
            position = _subsequence_position(words, node_words)
            if position is not None:
                positions.append((position, 0 if isinstance(node, Entity) else 1, node))
        return tuple(item[2] for item in sorted(positions, key=lambda item: item[:2]))

    def _shortest_path(
        self, model: MCDModel, source_id: str, target_id: str
    ) -> list[str]:
        if source_id == target_id:
            return [source_id]
        adjacency = self._adjacency(model)
        parents: dict[str, str | None] = {source_id: None}
        queue = deque([source_id])
        while queue:
            current = queue.popleft()
            for neighbor in sorted(adjacency.get(current, ())):
                if neighbor in parents:
                    continue
                parents[neighbor] = current
                if neighbor == target_id:
                    path = [target_id]
                    while parents[path[-1]] is not None:
                        parent = parents[path[-1]]
                        assert parent is not None
                        path.append(parent)
                    return list(reversed(path))
                queue.append(neighbor)
        return []

    @staticmethod
    def _adjacency(model: MCDModel) -> dict[str, set[str]]:
        adjacency: dict[str, set[str]] = {
            node_id: set() for node_id in (*model.entities, *model.associations)
        }
        for relation in model.relations.values():
            if relation.entity_id in adjacency and relation.association_id in adjacency:
                adjacency[relation.entity_id].add(relation.association_id)
                adjacency[relation.association_id].add(relation.entity_id)
        return adjacency

    @staticmethod
    def _relation_between(
        model: MCDModel, first_id: str, second_id: str
    ) -> Relation | None:
        return next(
            (
                relation
                for relation in model.relations.values()
                if {relation.entity_id, relation.association_id}
                == {first_id, second_id}
            ),
            None,
        )


def _normalized(value: str) -> str:
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore")
    return re.sub(r"[^a-z0-9]+", "_", ascii_value.decode().casefold()).strip("_")


def _stem(word: str) -> str:
    for suffix in (
        "ements",
        "ement",
        "ations",
        "ation",
        "eurs",
        "euses",
        "ent",
        "er",
        "es",
        "s",
        "e",
    ):
        if word.endswith(suffix) and len(word) - len(suffix) >= 4:
            return word[: -len(suffix)]
    return word


def _concept_matches(first: str, second: str) -> bool:
    ignored = {"de", "des", "du", "la", "le", "un", "une"}
    first_words = tuple(
        _stem(word) for word in first.split("_") if word and word not in ignored
    )
    second_words = tuple(
        _stem(word) for word in second.split("_") if word and word not in ignored
    )
    return first_words == second_words or set(first_words).issubset(second_words)


def _subsequence_position(words: list[str], candidate: list[str]) -> int | None:
    stemmed_words = [_stem(word) for word in words]
    stemmed_candidate = [_stem(word) for word in candidate]
    size = len(stemmed_candidate)
    for index in range(len(stemmed_words) - size + 1):
        if stemmed_words[index : index + size] == stemmed_candidate:
            return index
    return None
