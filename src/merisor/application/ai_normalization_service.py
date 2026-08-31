"""Suggestions facultatives de dépendances fonctionnelles via OpenRouter."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from merisor.application.openrouter_client import OpenRouterClient
from merisor.domain import Association, Entity


class AiNormalizationError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class AiDependencySuggestion:
    determinant_attribute_ids: tuple[str, ...]
    dependent_attribute_ids: tuple[str, ...]
    explanation: str


class AiNormalizationService:
    SYSTEM_PROMPT = """Tu aides à normaliser un modèle MERISE.
Retourne exclusivement un objet JSON de la forme :
{"dependencies":[{"determinants":["nom_attribut"],"dependents":["nom_attribut"],"explanation":"raison métier"}]}
N'invente aucun attribut. Une dépendance signifie que les déterminants fixent
une valeur unique pour chaque dépendant. Ne propose pas la dépendance triviale
d'un attribut vers lui-même. Une absence de certitude doit produire une liste vide.
Ces résultats sont des suggestions et seront confirmés par l'utilisateur."""

    def suggest(
        self,
        client: OpenRouterClient,
        model_id: str,
        owner: Entity | Association,
    ) -> tuple[AiDependencySuggestion, ...]:
        names = [attribute.name for attribute in owner.attributes]
        raw = client.complete(
            model_id,
            self.SYSTEM_PROMPT,
            f"Objet : {owner.name}\nAttributs autorisés : {json.dumps(names, ensure_ascii=False)}",
        )
        payload = self._parse_json(raw)
        raw_dependencies = payload.get("dependencies")
        if not isinstance(raw_dependencies, list):
            raise AiNormalizationError(
                "La réponse IA ne contient pas une liste 'dependencies'."
            )
        by_name = {
            attribute.name.casefold(): attribute.id for attribute in owner.attributes
        }
        suggestions: list[AiDependencySuggestion] = []
        for raw_dependency in raw_dependencies:
            if not isinstance(raw_dependency, dict):
                raise AiNormalizationError("Une suggestion IA est mal formée.")
            determinant_names = self._name_list(raw_dependency, "determinants")
            dependent_names = self._name_list(raw_dependency, "dependents")
            try:
                determinants = tuple(
                    by_name[name.casefold()] for name in determinant_names
                )
                dependents = tuple(by_name[name.casefold()] for name in dependent_names)
            except KeyError as error:
                raise AiNormalizationError(
                    f"L'IA a inventé un attribut inconnu : {error.args[0]}."
                ) from error
            if (
                not determinants
                or not dependents
                or set(determinants) & set(dependents)
            ):
                raise AiNormalizationError("Une suggestion IA est vide ou triviale.")
            explanation = raw_dependency.get("explanation", "")
            if not isinstance(explanation, str):
                explanation = ""
            suggestions.append(
                AiDependencySuggestion(determinants, dependents, explanation.strip())
            )
        return tuple(suggestions)

    @staticmethod
    def _parse_json(raw: str) -> dict[str, Any]:
        clean = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.I)
        try:
            payload = json.loads(clean)
        except json.JSONDecodeError as error:
            raise AiNormalizationError(
                "La réponse IA n'est pas un JSON valide."
            ) from error
        if not isinstance(payload, dict):
            raise AiNormalizationError("La réponse IA doit être un objet JSON.")
        return payload

    @staticmethod
    def _name_list(data: dict[str, Any], key: str) -> tuple[str, ...]:
        value = data.get(key)
        if not isinstance(value, list) or not all(
            isinstance(item, str) for item in value
        ):
            raise AiNormalizationError(
                f"Le champ IA '{key}' doit être une liste de noms."
            )
        return tuple(item.strip() for item in value if item.strip())
