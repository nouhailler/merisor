"""Génération et validation d'un projet MCD proposé par une IA."""

from __future__ import annotations

import json
from dataclasses import dataclass

from merisor.application.openrouter_client import OpenRouterClient
from merisor.domain import MCDModel, ValidationReport, validate_mcd
from merisor.persistence import JsonDiagramRepository, PersistenceError


SYSTEM_PROMPT = """Tu es un analyste MERISE chargé de produire un MCD.
Réponds uniquement avec un objet JSON valide, sans Markdown ni explication.
Le format obligatoire est MERISOR JSON version 2 :
{
  "format_version": 2,
  "entities": [
    {
      "id": "entity_x",
      "name": "NOM",
      "position": {"x": 100, "y": 100},
      "attributes": [
        {"id": "attribute_x", "name": "id_x", "identifier": true}
      ]
    }
  ],
  "associations": [
    {
      "id": "association_x",
      "name": "ASSOCIER",
      "position": {"x": 300, "y": 250},
      "attributes": [],
      "is_historized": false,
      "materialization_strategy": "AUTO"
    }
  ],
  "relations": [
    {
      "id": "relation_x",
      "entity_id": "entity_x",
      "association_id": "association_x",
      "cardinality": {"minimum": "0", "maximum": "N"}
    }
  ]
}

Règles obligatoires :
- chaque identifiant interne est une chaîne non vide et unique dans le document ;
- chaque entité possède un nom et au moins un attribut identifier=true ;
- une association relie au moins deux entités ;
- les cardinalités autorisées sont uniquement (0,1), (0,N), (1,1), (1,N) ;
- une relation relie toujours une entité existante à une association existante ;
- is_historized est un booléen explicite et n'est jamais déduit d'une date ;
- materialization_strategy vaut AUTO, FORCE_TABLE ou FORCE_FK ;
- n'utilise FORCE_FK que pour une association compatible et jamais avec is_historized=true ;
- répartis les positions afin de rendre le diagramme lisible ;
- n'ajoute aucune syntaxe SQL, aucun MLD et aucun commentaire hors JSON.
"""


class AiMcdValidationError(ValueError):
    """La réponse IA ne peut pas être convertie en projet MERISOR."""


@dataclass(frozen=True, slots=True)
class AiMcdCandidate:
    model: MCDModel
    report: ValidationReport
    json_text: str


class AiMcdService:
    def __init__(self, repository: JsonDiagramRepository | None = None) -> None:
        self.repository = repository or JsonDiagramRepository()

    def generate(self, client: OpenRouterClient, model_id: str, description: str) -> str:
        description = description.strip()
        if not description:
            raise AiMcdValidationError("La description de l'application est vide.")
        return client.complete(
            model_id,
            SYSTEM_PROMPT,
            "Conçois le MCD MERISE de l'application suivante :\n\n" + description,
        )

    def validate_json(self, text: str) -> AiMcdCandidate:
        json_text = self._extract_json(text)
        try:
            data = json.loads(json_text)
        except json.JSONDecodeError as error:
            raise AiMcdValidationError(
                f"JSON invalide à la ligne {error.lineno}, colonne {error.colno} : "
                f"{error.msg}."
            ) from error
        try:
            model = self.repository.from_dict(data)
        except PersistenceError as error:
            raise AiMcdValidationError(str(error)) from error
        report = validate_mcd(model)
        normalized = json.dumps(
            self.repository.to_dict(model), ensure_ascii=False, indent=2
        )
        return AiMcdCandidate(model, report, normalized + "\n")

    @staticmethod
    def _extract_json(text: str) -> str:
        candidate = text.strip()
        if candidate.startswith("```"):
            lines = candidate.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            candidate = "\n".join(lines).strip()
        start = candidate.find("{")
        end = candidate.rfind("}")
        if start < 0 or end < start:
            raise AiMcdValidationError("La réponse ne contient aucun objet JSON.")
        return candidate[start : end + 1]

