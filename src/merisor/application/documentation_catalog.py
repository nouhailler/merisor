"""Catalogue et localisation de la documentation Markdown de MERISOR."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path


class DocumentationError(ValueError):
    """La documentation demandée est absente ou inaccessible."""


@dataclass(frozen=True, slots=True)
class DocumentationPage:
    id: str
    title: str
    category: str
    relative_path: str


DOCUMENTATION_PAGES = (
    DocumentationPage("index", "Accueil de la documentation", "Accueil", "INDEX.md"),
    DocumentationPage(
        "getting-started", "Prise en main", "Utilisateur", "user/PRISE_EN_MAIN.md"
    ),
    DocumentationPage(
        "user-guide", "Guide utilisateur", "Utilisateur", "user/GUIDE_UTILISATEUR.md"
    ),
    DocumentationPage("mcd", "Créer un MCD", "Utilisateur", "user/MCD.md"),
    DocumentationPage("mld", "Comprendre le MLD", "Utilisateur", "user/MLD.md"),
    DocumentationPage("sql", "Générer du SQL", "Utilisateur", "user/SQL.md"),
    DocumentationPage("ai", "Fonctions IA", "Utilisateur", "user/IA.md"),
    DocumentationPage("faq", "Questions fréquentes", "Utilisateur", "user/FAQ.md"),
    DocumentationPage(
        "merise", "Comprendre MERISE", "Concepts MERISE", "concepts/MERISE.md"
    ),
    DocumentationPage(
        "mcd-mld-rules",
        "Règles MCD → MLD",
        "Concepts MERISE",
        "concepts/REGLES_MCD_MLD.md",
    ),
    DocumentationPage(
        "cardinalities",
        "Cardinalités",
        "Concepts MERISE",
        "concepts/CARDINALITES.md",
    ),
    DocumentationPage(
        "historization",
        "Historisation",
        "Concepts MERISE",
        "concepts/HISTORISATION.md",
    ),
    DocumentationPage(
        "normalization",
        "Normalisation",
        "Concepts MERISE",
        "concepts/NORMALISATION.md",
    ),
    DocumentationPage(
        "architecture", "Architecture", "Technique", "technical/ARCHITECTURE.md"
    ),
    DocumentationPage(
        "data-model", "Modèle de données", "Technique", "technical/DATA_MODEL.md"
    ),
    DocumentationPage(
        "json-format", "Format JSON V2", "Technique", "technical/JSON_FORMAT.md"
    ),
    DocumentationPage(
        "sql-dialects", "Dialectes SQL", "Technique", "technical/SQL_DIALECTS.md"
    ),
    DocumentationPage(
        "ai-architecture",
        "Architecture IA",
        "Technique",
        "technical/AI_ARCHITECTURE.md",
    ),
    DocumentationPage(
        "persistence", "Persistance", "Technique", "technical/PERSISTENCE.md"
    ),
    DocumentationPage(
        "security", "Sécurité et confidentialité", "Technique", "technical/SECURITY.md"
    ),
    DocumentationPage(
        "development",
        "Environnement développeur",
        "Développement",
        "development/DEVELOPMENT.md",
    ),
    DocumentationPage("tests", "Tests", "Développement", "development/TESTS.md"),
    DocumentationPage(
        "contributing", "Contribuer", "Développement", "development/CONTRIBUTING.md"
    ),
    DocumentationPage(
        "release", "Publier une version", "Développement", "development/RELEASE.md"
    ),
    DocumentationPage(
        "packaging", "Packaging Linux", "Développement", "development/PACKAGING.md"
    ),
    DocumentationPage(
        "codex-guide", "Guide Codex", "Développement", "development/CODEX_GUIDE.md"
    ),
    DocumentationPage(
        "project-context", "Contexte et décisions", "Projet", "decisions/CONTEXT.md"
    ),
)


class DocumentationCatalog:
    """Résout les pages depuis les sources, une installation ou PyInstaller."""

    def __init__(self, root: Path | None = None) -> None:
        self._explicit_root = root
        self._pages = {page.id: page for page in DOCUMENTATION_PAGES}

    @property
    def pages(self) -> tuple[DocumentationPage, ...]:
        return DOCUMENTATION_PAGES

    @property
    def root(self) -> Path:
        candidates = self._candidate_roots()
        for candidate in candidates:
            if (candidate / "INDEX.md").is_file():
                return candidate.resolve()
        searched = "\n".join(f"- {candidate}" for candidate in candidates)
        raise DocumentationError(
            "La documentation locale de MERISOR est introuvable.\n" + searched
        )

    def page(self, page_id: str) -> DocumentationPage:
        try:
            return self._pages[page_id]
        except KeyError as error:
            raise DocumentationError(
                f"Page de documentation inconnue : {page_id}"
            ) from error

    def path(self, page_id: str) -> Path:
        page = self.page(page_id)
        path = (self.root / page.relative_path).resolve()
        if not path.is_relative_to(self.root) or not path.is_file():
            raise DocumentationError(
                f"Page de documentation absente : {page.relative_path}"
            )
        return path

    def page_id_for_path(self, path: Path) -> str | None:
        resolved = path.resolve()
        for page in self.pages:
            if (self.root / page.relative_path).resolve() == resolved:
                return page.id
        return None

    def _candidate_roots(self) -> tuple[Path, ...]:
        if self._explicit_root is not None:
            return (self._explicit_root,)
        configured = os.environ.get("MERISOR_DOCS_DIR")
        candidates: list[Path] = []
        if configured:
            candidates.append(Path(configured))
        frozen_root = getattr(sys, "_MEIPASS", None)
        if isinstance(frozen_root, str):
            candidates.append(Path(frozen_root) / "docs")
        candidates.extend(
            (
                Path(__file__).resolve().parents[3] / "docs",
                Path(sys.prefix) / "share" / "doc" / "merisor",
                Path(sys.executable).resolve().parent.parent
                / "share"
                / "doc"
                / "merisor",
                Path("/usr/share/doc/merisor"),
            )
        )
        # Préserve l'ordre tout en évitant les doublons.
        return tuple(dict.fromkeys(candidates))
