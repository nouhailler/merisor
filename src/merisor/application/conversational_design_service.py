"""Service OpenRouter de conception conversationnelle par patchs MCD stricts."""

from __future__ import annotations

import json
from dataclasses import replace
from typing import Any

from merisor.domain import validate_mcd
from merisor.persistence import JsonDiagramRepository

from .design_session import (
    ConceptKind,
    DesignAssistantResponse,
    DesignQuestion,
    DesignSession,
    DesignSessionError,
    DesignStep,
    DetectedConcept,
    DraftPatch,
    DraftPatchApplier,
)
from .openrouter_client import OpenRouterClient

CONVERSATIONAL_SYSTEM_PROMPT = """Tu es un assistant de conception MERISE.
Tu travailles toujours sur le brouillon JSON fourni par MERISOR et tu réponds
exclusivement avec un objet JSON, sans Markdown.

Format racine exact :
{
  "assistant_message": "explication courte et pédagogique",
  "detected_concepts": [
    {"name":"LIVRE","kind":"entity","confidence":0.95}
  ],
  "questions": [
    {
      "id":"book_authors",
      "text":"Un livre peut-il avoir plusieurs auteurs ?",
      "choices":["Oui","Non"],
      "impact":"Détermine la cardinalité de ECRIRE."
    }
  ],
  "assumptions": ["Les emprunts rendus sont conservés."],
  "draft_patch": {
    "entities_to_add": [],
    "entities_to_update": [],
    "entity_ids_to_remove": [],
    "associations_to_add": [],
    "associations_to_update": [],
    "association_ids_to_remove": [],
    "relations_to_add": [],
    "relations_to_update": [],
    "relation_ids_to_remove": [],
    "inheritances_to_add": [],
    "inheritances_to_update": [],
    "inheritance_ids_to_remove": [],
    "functional_dependencies_to_add": [],
    "functional_dependencies_to_update": [],
    "functional_dependency_ids_to_remove": []
  },
  "ready_for_preview": false
}

Une addition contient l'objet MERISOR V2 complet avec un ID stable et unique.
Une mise à jour vaut {"id":"id_existant","changes":{"champ": valeur}} et ne
modifie jamais l'ID. Une suppression contient seulement un ID existant.

Règles :
- ne renvoie jamais le MCD complet, uniquement un patch par rapport au brouillon ;
- conserve les IDs existants ; utilise des IDs lisibles et stables pour les ajouts ;
- une entité ajoutée contient id, name, position et attributes ;
- un attribut contient id, name, identifier, data_type, nullable, default,
  unique, comment, auto_increment et constraints ;
- data_type vaut null ou un objet {"name":"VARCHAR","length":100} ; les noms
  autorisés sont INTEGER, BIGINT, DECIMAL, FLOAT, BOOLEAN, VARCHAR, TEXT, DATE,
  TIME, DATETIME et TIMESTAMP ;
- une association contient id, name, position, attributes, is_historized et
  materialization_strategy ;
- materialization_strategy vaut AUTO, FORCE_TABLE ou FORCE_FK ;
- une relation contient id, entity_id, association_id, role et cardinality ;
- cardinality est exactement {"minimum":"0","maximum":"N"} ; seules les
  combinaisons (0,1), (0,N), (1,1), (1,N) sont autorisées ;
- une spécialisation contient id, parent_entity_id, child_entity_ids et strategy
  (PARENT_ONLY, CHILDREN_ONLY ou JOINED) ;
- une dépendance fonctionnelle contient id, owner_id,
  determinant_attribute_ids, dependent_attribute_ids et origin (AI) ;
- pour modifier un attribut, renvoie une mise à jour de son entité ou association
  avec la liste attributes complète dans changes ;
- pose une question lorsqu'une réponse change les cardinalités, l'historisation,
  l'identification ou le choix entité/association ;
- ne pose pas de question cosmétique et regroupe les questions importantes ;
- n'invente pas une décision métier silencieusement : rends-la dans assumptions ;
- ready_for_preview vaut true seulement lorsque le brouillon est suffisamment
  cohérent et que les questions structurantes sont résolues ;
- confidence est un nombre entre 0 et 1 ; kind vaut entity, association ou attribute.
"""


class ConversationalDesignService:
    def __init__(
        self,
        repository: JsonDiagramRepository | None = None,
        applier: DraftPatchApplier | None = None,
    ) -> None:
        self.repository = repository or JsonDiagramRepository()
        self.applier = applier or DraftPatchApplier(self.repository)

    def generate_step(
        self,
        client: OpenRouterClient,
        model_id: str,
        session: DesignSession,
        user_message: str,
    ) -> DesignStep:
        clean_message = user_message.strip()
        if not clean_message:
            raise DesignSessionError("Le message utilisateur est vide.")
        raw = client.complete(
            model_id,
            CONVERSATIONAL_SYSTEM_PROMPT,
            self._user_prompt(session, clean_message),
        )
        return self.interpret(session, raw)

    def interpret(self, session: DesignSession, raw: str) -> DesignStep:
        payload = self._payload(raw)
        response = self._response(payload)
        draft_model, patch_summary = self.applier.apply(
            session.current_draft, response.draft_patch
        )
        report = validate_mcd(draft_model)
        if (report.errors or response.questions) and response.ready_for_preview:
            response = replace(response, ready_for_preview=False)
        draft_json = (
            json.dumps(
                self.repository.to_dict(draft_model), ensure_ascii=False, indent=2
            )
            + "\n"
        )
        return DesignStep(response, draft_model, draft_json, report, patch_summary)

    @staticmethod
    def _user_prompt(session: DesignSession, message: str) -> str:
        turns = "\n".join(
            f"Utilisateur: {turn.user_message}\nAssistant: {turn.assistant_message}"
            for turn in session.turns[-6:]
        )
        assumptions = json.dumps(session.assumptions, ensure_ascii=False)
        answers = json.dumps(session.answered_questions, ensure_ascii=False)
        return (
            f"Message actuel de l'utilisateur :\n{message}\n\n"
            f"Historique synthétique :\n{turns or '(premier tour)'}\n\n"
            f"Hypothèses déjà retenues : {assumptions}\n"
            f"Réponses structurées connues : {answers}\n\n"
            "Brouillon MERISOR V2 courant :\n"
            f"{session.current_json()}"
        )

    @classmethod
    def _payload(cls, raw: str) -> dict[str, Any]:
        candidate = raw.strip()
        if candidate.startswith("```"):
            lines = candidate.splitlines()[1:]
            if lines and lines[-1].strip() == "```":
                lines.pop()
            candidate = "\n".join(lines).strip()
        start = candidate.find("{")
        end = candidate.rfind("}")
        if start < 0 or end < start:
            raise DesignSessionError("La réponse IA ne contient aucun objet JSON.")
        try:
            payload = json.loads(candidate[start : end + 1])
        except json.JSONDecodeError as error:
            raise DesignSessionError(
                f"Réponse conversationnelle JSON invalide : {error.msg}."
            ) from error
        if not isinstance(payload, dict):
            raise DesignSessionError("La réponse conversationnelle doit être un objet.")
        expected = {
            "assistant_message",
            "detected_concepts",
            "questions",
            "assumptions",
            "draft_patch",
            "ready_for_preview",
        }
        if set(payload) != expected:
            missing = expected - set(payload)
            unknown = set(payload) - expected
            details = []
            if missing:
                details.append("manquants : " + ", ".join(sorted(missing)))
            if unknown:
                details.append("inconnus : " + ", ".join(sorted(unknown)))
            raise DesignSessionError(
                "Champs racine invalides (" + "; ".join(details) + ")."
            )
        return payload

    @classmethod
    def _response(cls, payload: dict[str, Any]) -> DesignAssistantResponse:
        assistant_message = cls._nonempty_text(payload, "assistant_message")
        concepts = cls._concepts(payload.get("detected_concepts"))
        questions = cls._questions(payload.get("questions"))
        assumptions = cls._text_list(payload.get("assumptions"), "assumptions")
        patch = cls.parse_patch(payload.get("draft_patch"))
        ready = payload.get("ready_for_preview")
        if not isinstance(ready, bool):
            raise DesignSessionError("ready_for_preview doit être booléen.")
        return DesignAssistantResponse(
            assistant_message,
            concepts,
            questions,
            assumptions,
            patch,
            ready,
        )

    @classmethod
    def _concepts(cls, raw: Any) -> tuple[DetectedConcept, ...]:
        if not isinstance(raw, list):
            raise DesignSessionError("detected_concepts doit être une liste.")
        concepts: list[DetectedConcept] = []
        for item in raw:
            if not isinstance(item, dict) or set(item) != {
                "name",
                "kind",
                "confidence",
            }:
                raise DesignSessionError("Un concept détecté est mal formé.")
            name = cls._nonempty_text(item, "name")
            try:
                kind = ConceptKind(item.get("kind"))
            except (TypeError, ValueError) as error:
                raise DesignSessionError("Type de concept IA invalide.") from error
            confidence = item.get("confidence")
            if (
                not isinstance(confidence, (int, float))
                or isinstance(confidence, bool)
                or not 0 <= float(confidence) <= 1
            ):
                raise DesignSessionError(
                    "La confiance d'un concept doit être entre 0 et 1."
                )
            concepts.append(DetectedConcept(name, kind, float(confidence)))
        return tuple(concepts)

    @classmethod
    def _questions(cls, raw: Any) -> tuple[DesignQuestion, ...]:
        if not isinstance(raw, list):
            raise DesignSessionError("questions doit être une liste.")
        questions: list[DesignQuestion] = []
        seen: set[str] = set()
        for item in raw:
            if not isinstance(item, dict) or set(item) != {
                "id",
                "text",
                "choices",
                "impact",
            }:
                raise DesignSessionError("Une question IA est mal formée.")
            question_id = cls._nonempty_text(item, "id")
            if question_id in seen:
                raise DesignSessionError(f"Question dupliquée : {question_id}")
            seen.add(question_id)
            questions.append(
                DesignQuestion(
                    question_id,
                    cls._nonempty_text(item, "text"),
                    cls._text_list(item.get("choices"), "choices"),
                    cls._text(item, "impact"),
                )
            )
        return tuple(questions)

    @classmethod
    def parse_patch(cls, raw: Any) -> DraftPatch:
        """Valide le format public d'un patch MCD contrôlé."""

        if not isinstance(raw, dict):
            raise DesignSessionError("draft_patch doit être un objet.")
        specs = {
            "entities": (
                "entities_to_add",
                "entities_to_update",
                "entity_ids_to_remove",
            ),
            "associations": (
                "associations_to_add",
                "associations_to_update",
                "association_ids_to_remove",
            ),
            "relations": (
                "relations_to_add",
                "relations_to_update",
                "relation_ids_to_remove",
            ),
            "inheritances": (
                "inheritances_to_add",
                "inheritances_to_update",
                "inheritance_ids_to_remove",
            ),
            "functional_dependencies": (
                "functional_dependencies_to_add",
                "functional_dependencies_to_update",
                "functional_dependency_ids_to_remove",
            ),
        }
        expected = {key for keys in specs.values() for key in keys}
        if set(raw) != expected:
            raise DesignSessionError(
                "draft_patch ne respecte pas le schéma strict attendu."
            )
        additions: dict[str, tuple[dict[str, Any], ...]] = {}
        updates: dict[str, tuple[dict[str, Any], ...]] = {}
        removals: dict[str, tuple[str, ...]] = {}
        for collection, (add_key, update_key, remove_key) in specs.items():
            additions[collection] = cls._object_list(raw.get(add_key), add_key)
            updates[collection] = cls._object_list(raw.get(update_key), update_key)
            removals[collection] = cls._text_list(raw.get(remove_key), remove_key)
        return DraftPatch(additions, updates, removals)

    @staticmethod
    def _object_list(raw: Any, key: str) -> tuple[dict[str, Any], ...]:
        if not isinstance(raw, list) or not all(isinstance(item, dict) for item in raw):
            raise DesignSessionError(f"{key} doit être une liste d'objets.")
        return tuple(raw)

    @staticmethod
    def _text_list(raw: Any, key: str) -> tuple[str, ...]:
        if not isinstance(raw, list) or not all(isinstance(item, str) for item in raw):
            raise DesignSessionError(f"{key} doit être une liste de textes.")
        return tuple(item.strip() for item in raw if item.strip())

    @staticmethod
    def _nonempty_text(data: dict[str, Any], key: str) -> str:
        value = data.get(key)
        if not isinstance(value, str) or not value.strip():
            raise DesignSessionError(f"{key} doit être un texte non vide.")
        return value.strip()

    @staticmethod
    def _text(data: dict[str, Any], key: str) -> str:
        value = data.get(key, "")
        if not isinstance(value, str):
            raise DesignSessionError(f"{key} doit être textuel.")
        return value.strip()
