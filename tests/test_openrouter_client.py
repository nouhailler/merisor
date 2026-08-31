from __future__ import annotations

import pytest

from merisor.application import OpenRouterClient, OpenRouterError


def test_free_text_models_are_filtered_and_json_models_sorted() -> None:
    client = OpenRouterClient("sk-or-test")
    client._get = lambda _path: {  # type: ignore[assignment,method-assign]
        "data": [
            {
                "id": "paid/model",
                "name": "Paid",
                "pricing": {"prompt": "1", "completion": "1"},
                "architecture": {
                    "input_modalities": ["text"],
                    "output_modalities": ["text"],
                },
            },
            {
                "id": "free/model:free",
                "name": "Free",
                "pricing": {"prompt": "0", "completion": "0"},
                "architecture": {
                    "input_modalities": ["text"],
                    "output_modalities": ["text"],
                },
                "supported_parameters": ["response_format"],
            },
            {
                "id": "free/image:free",
                "name": "Image",
                "pricing": {"prompt": "0", "completion": "0"},
                "architecture": {
                    "input_modalities": ["image"],
                    "output_modalities": ["text"],
                },
            },
        ]
    }
    models = client.list_models()
    assert [model.id for model in models] == ["free/model:free"]
    assert models[0].supports_json


def test_openrouter_missing_key_is_readable() -> None:
    with pytest.raises(OpenRouterError, match="Aucune clé"):
        OpenRouterClient("").test_key()
