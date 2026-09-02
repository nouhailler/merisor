"""Analyse IA non destructive d'un MCD existant par patchs contrôlés."""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from enum import Enum
from typing import Any

from merisor.application.conversational_design_service import (
    ConversationalDesignService,
)
from merisor.application.design_session import (
    DesignSessionError,
    DraftPatch,
    DraftPatchApplier,
)
from merisor.application.openrouter_client import OpenRouterClient
from merisor.domain import (
    MCDModel,
    ValidationReport,
    analyze_model_quality,
    validate_mcd,
)
from merisor.persistence import JsonDiagramRepository


class AiRepairError(ValueError):
    """Une réponse de réparation n'est pas exploitable de manière sûre."""


class RepairConfidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

    @property
    def label(self) -> str:
        return {
            RepairConfidence.HIGH: "Élevée",
            RepairConfidence.MEDIUM: "Moyenne",
            RepairConfidence.LOW: "Faible",
        }[self]


@dataclass(frozen=True, slots=True)
class AiRepairProposal:
    id: str
    title: str
    description: str
    rationale: str
    confidence: RepairConfidence
    patch: DraftPatch
    candidate: MCDModel
    validation: ValidationReport
    patch_summary: str


@dataclass(frozen=True, slots=True)
class AiRepairReport:
    summary: str
    proposals: tuple[AiRepairProposal, ...]
    raw_json: str


REPAIR_SYSTEM_PROMPT = """Tu analyses un MCD MERISOR V2 existant.
Réponds exclusivement avec un objet JSON, sans Markdown :
{
  "summary":"résumé court",
  "proposals":[
    {
      "id":"unique_email_client",
      "title":"Rendre CLIENT.email unique",
      "description":"CLIENT.email devrait probablement être UNIQUE.",
      "rationale":"Un email sert souvent d'identifiant métier.",
      "confidence":"medium",
      "patch": {
        "entities_to_add": [], "entities_to_update": [],
        "entity_ids_to_remove": [], "associations_to_add": [],
        "associations_to_update": [], "association_ids_to_remove": [],
        "relations_to_add": [], "relations_to_update": [],
        "relation_ids_to_remove": [], "inheritances_to_add": [],
        "inheritances_to_update": [], "inheritance_ids_to_remove": [],
        "functional_dependencies_to_add": [],
        "functional_dependencies_to_update": [],
        "functional_dependency_ids_to_remove": []
      }
    }
  ]
}

Chaque proposition doit être autonome et porter un patch au format MERISOR
strict. Une mise à jour vaut {"id":"id_existant","changes":{...}} et ne
modifie jamais un ID. Pour modifier un attribut, renvoie la liste complète des
attributs de son entité ou association dans changes. Conserve tous les IDs
existants et n'invente aucun ID de référence. Une addition contient l'objet V2
complet avec un nouvel ID unique. Les suppressions doivent être rares et
justifiées. confidence vaut high, medium ou low.

Propose uniquement des améliorations plausibles : types, unicité, attributs
redondants, cardinalités, associations, entités métier, historisation ou
normalisation. Une ambiguïté métier doit produire une proposition de confiance
faible, jamais une affirmation. Ne répète pas une correction déjà présente.
Ne génère ni SQL ni MLD. Retourne au maximum 12 propositions. Une absence
d'amélioration doit produire proposals: []. Aucune proposition ne sera
appliquée automatiquement : l'utilisateur les examinera une par une."""


class AiRepairService:
    def __init__(
        self,
        repository: JsonDiagramRepository | None = None,
        applier: DraftPatchApplier | None = None,
    ) -> None:
        self.repository = repository or JsonDiagramRepository()
        self.applier = applier or DraftPatchApplier(self.repository)

    def analyze(self, client: OpenRouterClient, model_id: str, model: MCDModel) -> str:
        return client.complete(
            model_id,
            REPAIR_SYSTEM_PROMPT,
            self._user_prompt(model),
        )

    def interpret(self, model: MCDModel, raw: str) -> AiRepairReport:
        payload, normalized = self._payload(raw)
        if set(payload) != {"summary", "proposals"}:
            raise AiRepairError("La réponse doit contenir summary et proposals.")
        summary = self._text(payload, "summary", allow_empty=True)
        raw_proposals = payload.get("proposals")
        if not isinstance(raw_proposals, list):
            raise AiRepairError("Le champ proposals doit être une liste.")
        if len(raw_proposals) > 12:
            raise AiRepairError("L'IA a renvoyé plus de 12 propositions.")
        proposals: list[AiRepairProposal] = []
        seen: set[str] = set()
        for raw_proposal in raw_proposals:
            proposal = self._proposal(model, raw_proposal)
            if proposal.id in seen:
                raise AiRepairError(f"Proposition dupliquée : {proposal.id}.")
            seen.add(proposal.id)
            proposals.append(proposal)
        return AiRepairReport(summary, tuple(proposals), normalized)

    def combine(
        self,
        model: MCDModel,
        report: AiRepairReport,
        proposal_ids: set[str],
    ) -> tuple[MCDModel, ValidationReport, str]:
        if not proposal_ids:
            raise AiRepairError("Sélectionnez au moins une proposition à appliquer.")
        known = {proposal.id for proposal in report.proposals}
        unknown = proposal_ids - known
        if unknown:
            raise AiRepairError(f"Proposition inconnue : {sorted(unknown)[0]}.")
        touched: dict[tuple[str, str, str], str] = {}
        for proposal in report.proposals:
            if proposal.id not in proposal_ids:
                continue
            for collection, updates in proposal.patch.updates.items():
                for update in updates:
                    update_id = update.get("id")
                    changes = update.get("changes")
                    if not isinstance(update_id, str) or not isinstance(changes, dict):
                        continue
                    for key in changes:
                        address = (collection, update_id, key)
                        previous = touched.get(address)
                        if previous is not None:
                            raise AiRepairError(
                                "Les propositions sélectionnées modifient toutes deux "
                                f"{collection}:{update_id}.{key} ({previous} et "
                                f"{proposal.title}). Appliquez-les séparément."
                            )
                        touched[address] = proposal.title
        candidate = copy.deepcopy(model)
        summaries: list[str] = []
        try:
            for proposal in report.proposals:
                if proposal.id in proposal_ids:
                    candidate, summary = self.applier.apply(candidate, proposal.patch)
                    summaries.append(f"{proposal.title}\n{summary}")
        except DesignSessionError as error:
            raise AiRepairError(
                "Les propositions sélectionnées sont incompatibles entre elles : "
                f"{error}"
            ) from error
        return candidate, validate_mcd(candidate), "\n\n".join(summaries)

    def _proposal(self, model: MCDModel, raw: Any) -> AiRepairProposal:
        if not isinstance(raw, dict) or set(raw) != {
            "id",
            "title",
            "description",
            "rationale",
            "confidence",
            "patch",
        }:
            raise AiRepairError("Une proposition IA est mal formée.")
        proposal_id = self._text(raw, "id")
        try:
            confidence = RepairConfidence(raw.get("confidence"))
        except (TypeError, ValueError) as error:
            raise AiRepairError(
                "Le niveau de confiance d'une proposition est invalide."
            ) from error
        try:
            patch = ConversationalDesignService.parse_patch(raw.get("patch"))
            candidate, patch_summary = self.applier.apply(model, patch)
        except DesignSessionError as error:
            raise AiRepairError(
                f"La proposition {proposal_id} contient un patch invalide : {error}"
            ) from error
        if patch.empty:
            raise AiRepairError(f"La proposition {proposal_id} ne change rien au MCD.")
        if self.repository.to_dict(candidate) == self.repository.to_dict(model):
            raise AiRepairError(f"La proposition {proposal_id} ne change rien au MCD.")
        return AiRepairProposal(
            proposal_id,
            self._text(raw, "title"),
            self._text(raw, "description"),
            self._text(raw, "rationale"),
            confidence,
            patch,
            candidate,
            validate_mcd(candidate),
            patch_summary,
        )

    def _user_prompt(self, model: MCDModel) -> str:
        validation = validate_mcd(model)
        quality = analyze_model_quality(model, validation)
        signals = [
            {
                "code": finding.code,
                "message": finding.message,
                "rationale": finding.rationale,
                "confidence": finding.confidence.value,
            }
            for finding in quality.findings
        ]
        context = {
            "validation": [issue.message for issue in validation.issues],
            "local_quality_signals": signals,
            "mcd": self.repository.to_dict(model),
        }
        return (
            "Analyse ce MCD existant. Les signaux locaux sont des indices à vérifier, "
            "pas des vérités métier.\n"
            + json.dumps(context, ensure_ascii=False, indent=2)
        )

    @staticmethod
    def _payload(raw: str) -> tuple[dict[str, Any], str]:
        candidate = raw.strip()
        if candidate.startswith("```"):
            lines = candidate.splitlines()[1:]
            if lines and lines[-1].strip() == "```":
                lines.pop()
            candidate = "\n".join(lines).strip()
        start, end = candidate.find("{"), candidate.rfind("}")
        if start < 0 or end < start:
            raise AiRepairError("La réponse IA ne contient aucun objet JSON.")
        try:
            payload = json.loads(candidate[start : end + 1])
        except json.JSONDecodeError as error:
            raise AiRepairError(f"Réponse IA JSON invalide : {error.msg}.") from error
        if not isinstance(payload, dict):
            raise AiRepairError("La réponse IA doit être un objet JSON.")
        normalized = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
        return payload, normalized

    @staticmethod
    def _text(data: dict[str, Any], key: str, *, allow_empty: bool = False) -> str:
        value = data.get(key)
        if not isinstance(value, str) or (not allow_empty and not value.strip()):
            raise AiRepairError(f"Le champ {key} doit être un texte non vide.")
        return value.strip()
