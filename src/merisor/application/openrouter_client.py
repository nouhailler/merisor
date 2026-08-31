"""Client minimal et indépendant de l'interface pour OpenRouter."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, TypeAlias
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from merisor import __version__

JsonObject: TypeAlias = dict[str, Any]


class OpenRouterError(RuntimeError):
    """Erreur réseau ou réponse OpenRouter inexploitable."""


@dataclass(frozen=True, slots=True)
class OpenRouterModel:
    id: str
    name: str
    prompt_price: float
    completion_price: float
    supports_json: bool = False

    @property
    def is_free(self) -> bool:
        return self.id.endswith(":free") or (
            self.prompt_price == 0 and self.completion_price == 0
        )


class OpenRouterClient:
    BASE_URL = "https://openrouter.ai/api/v1"

    def __init__(self, api_key: str, timeout: float = 15.0) -> None:
        self.api_key = api_key.strip()
        self.timeout = timeout

    def _get(self, path: str) -> JsonObject:
        if not self.api_key:
            raise OpenRouterError("Aucune clé OpenRouter n'est configurée.")
        request = Request(
            f"{self.BASE_URL}{path}",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Accept": "application/json",
                "User-Agent": f"MERISOR/{__version__}",
            },
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            if error.code in {401, 403}:
                raise OpenRouterError("La clé OpenRouter est refusée.") from error
            raise OpenRouterError(f"OpenRouter a répondu HTTP {error.code}.") from error
        except (URLError, TimeoutError, OSError, json.JSONDecodeError) as error:
            raise OpenRouterError(
                f"Impossible de contacter OpenRouter : {error}"
            ) from error
        if not isinstance(payload, dict):
            raise OpenRouterError("Réponse OpenRouter invalide.")
        return payload

    def _post(self, path: str, data: JsonObject) -> JsonObject:
        if not self.api_key:
            raise OpenRouterError("Aucune clé OpenRouter n'est configurée.")
        request = Request(
            f"{self.BASE_URL}{path}",
            data=json.dumps(data).encode("utf-8"),
            method="POST",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": f"MERISOR/{__version__}",
                "HTTP-Referer": "https://github.com/nouhailler/merisor",
                "X-Title": "MERISOR",
            },
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            if error.code in {401, 403}:
                raise OpenRouterError("La clé OpenRouter est refusée.") from error
            if error.code == 429:
                raise OpenRouterError(
                    "Quota ou limite OpenRouter atteint. Réessayez plus tard."
                ) from error
            raise OpenRouterError(f"OpenRouter a répondu HTTP {error.code}.") from error
        except (URLError, TimeoutError, OSError, json.JSONDecodeError) as error:
            raise OpenRouterError(
                f"Impossible de contacter OpenRouter : {error}"
            ) from error
        if not isinstance(payload, dict):
            raise OpenRouterError("Réponse OpenRouter invalide.")
        return payload

    def test_key(self) -> None:
        self._get("/models")

    def list_models(self) -> list[OpenRouterModel]:
        payload = self._get("/models")
        raw_models = payload.get("data")
        if not isinstance(raw_models, list):
            raise OpenRouterError("La réponse OpenRouter ne contient pas de modèles.")
        models: list[OpenRouterModel] = []
        for raw in raw_models:
            if not isinstance(raw, dict):
                continue
            architecture = raw.get("architecture") or {}
            input_modalities = architecture.get("input_modalities", [])
            output_modalities = architecture.get("output_modalities", [])
            if "text" not in input_modalities or "text" not in output_modalities:
                continue
            pricing = raw.get("pricing") or {}
            try:
                model = OpenRouterModel(
                    id=str(raw["id"]),
                    name=str(raw.get("name") or raw["id"]),
                    prompt_price=float(pricing.get("prompt", 0)),
                    completion_price=float(pricing.get("completion", 0)),
                    supports_json="response_format"
                    in (raw.get("supported_parameters") or []),
                )
            except (KeyError, TypeError, ValueError):
                continue
            if model.is_free:
                models.append(model)
        return sorted(
            models, key=lambda model: (not model.supports_json, model.name.lower())
        )

    def complete(self, model_id: str, system_prompt: str, user_prompt: str) -> str:
        if not model_id.strip():
            raise OpenRouterError("Aucun modèle OpenRouter n'est sélectionné.")
        payload = self._post(
            "/chat/completions",
            {
                "model": model_id,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.1,
            },
        )
        try:
            content = payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as error:
            raise OpenRouterError(
                "La réponse OpenRouter ne contient aucun texte exploitable."
            ) from error
        if not isinstance(content, str) or not content.strip():
            raise OpenRouterError("OpenRouter a renvoyé une réponse vide.")
        return content.strip()
