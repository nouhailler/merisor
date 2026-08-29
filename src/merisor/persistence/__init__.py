"""Persistance des diagrammes."""

from merisor.persistence.json_repository import (
    FORMAT_VERSION,
    LEGACY_FORMAT_VERSION,
    JsonDiagramRepository,
    PersistenceError,
)

__all__ = [
    "FORMAT_VERSION",
    "LEGACY_FORMAT_VERSION",
    "JsonDiagramRepository",
    "PersistenceError",
]
