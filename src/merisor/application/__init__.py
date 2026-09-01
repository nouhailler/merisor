"""Logique applicative et coordination modèle-interface."""

from merisor.application.ai_mcd_service import (
    AiMcdCandidate,
    AiMcdService,
    AiMcdValidationError,
)
from merisor.application.ai_normalization_service import (
    AiDependencySuggestion,
    AiNormalizationError,
    AiNormalizationService,
)
from merisor.application.controller import DiagramController, MLDGenerationBlocked
from merisor.application.conversational_design_service import (
    CONVERSATIONAL_SYSTEM_PROMPT,
    ConversationalDesignService,
)
from merisor.application.ddl_importer import (
    DDLImportError,
    DDLImportResult,
    SQLDDLImporter,
)
from merisor.application.design_session import (
    ConceptKind,
    DesignAssistantResponse,
    DesignQuestion,
    DesignSession,
    DesignSessionError,
    DesignStep,
    DetectedConcept,
    DraftPatch,
    DraftPatchApplier,
    DraftRevision,
    ModelDifference,
    compare_models,
)
from merisor.application.diagram_text_exporter import (
    DiagramTextExporter,
    DiagramTextExportError,
    DiagramTextFormat,
)
from merisor.application.documentation_generator import (
    ModelDocumentation,
    ModelDocumentationGenerator,
)
from merisor.application.impact_analysis import (
    ImpactCertainty,
    ImpactReference,
    ImpactReport,
    ImpactTarget,
    ModelImpactAnalyzer,
)
from merisor.application.mcd_layout import McdAutoLayout
from merisor.application.mld_text import render_mld_text
from merisor.application.mld_transformer import (
    McdToMldTransformer,
    MLDNamePolicy,
    MLDTransformationError,
    mcd_logical_fingerprint,
)
from merisor.application.model_explorer import (
    ExplorationOptions,
    ExplorationResult,
    ExplorationSearchResult,
    ModelExplorer,
)
from merisor.application.openrouter_client import (
    OpenRouterClient,
    OpenRouterError,
    OpenRouterModel,
)
from merisor.application.openrouter_settings import OpenRouterKeyStore
from merisor.application.query_generator import (
    QueryGenerationError,
    QueryGenerationResult,
    QueryTarget,
    SQLQueryGenerator,
)
from merisor.application.sql_generator import (
    MLDSQLValidator,
    MySQLDialect,
    PostgreSQLDialect,
    SQLDialect,
    SQLGenerationError,
    SQLGenerationOptions,
    SQLGenerator,
    SQLiteDialect,
    SQLTarget,
    SQLValidationIssue,
    SQLValidationReport,
    SQLValidationSeverity,
    sql_dialect,
)
from merisor.application.submodels import (
    GLOBAL_SCOPE_ID,
    SubmodelResolver,
    SubmodelScope,
)
from merisor.application.test_data_generator import (
    TestDataGenerationError,
    TestDataGenerationResult,
    TestDataGenerator,
    TestDataIssue,
)
from merisor.application.version_comparator import (
    ChangeImpact,
    ChangeKind,
    ModelVersionComparator,
    VersionChange,
    VersionComparison,
)

__all__ = [
    "CONVERSATIONAL_SYSTEM_PROMPT",
    "GLOBAL_SCOPE_ID",
    "AiDependencySuggestion",
    "AiMcdCandidate",
    "AiMcdService",
    "AiMcdValidationError",
    "AiNormalizationError",
    "AiNormalizationService",
    "ChangeImpact",
    "ChangeKind",
    "ConceptKind",
    "ConversationalDesignService",
    "DDLImportError",
    "DDLImportResult",
    "DesignAssistantResponse",
    "DesignQuestion",
    "DesignSession",
    "DesignSessionError",
    "DesignStep",
    "DetectedConcept",
    "DiagramController",
    "DiagramTextExportError",
    "DiagramTextExporter",
    "DiagramTextFormat",
    "DraftPatch",
    "DraftPatchApplier",
    "DraftRevision",
    "ExplorationOptions",
    "ExplorationResult",
    "ExplorationSearchResult",
    "ImpactCertainty",
    "ImpactReference",
    "ImpactReport",
    "ImpactTarget",
    "MLDGenerationBlocked",
    "MLDNamePolicy",
    "MLDSQLValidator",
    "MLDTransformationError",
    "McdAutoLayout",
    "McdToMldTransformer",
    "ModelDifference",
    "ModelDocumentation",
    "ModelDocumentationGenerator",
    "ModelExplorer",
    "ModelImpactAnalyzer",
    "ModelVersionComparator",
    "MySQLDialect",
    "OpenRouterClient",
    "OpenRouterError",
    "OpenRouterKeyStore",
    "OpenRouterModel",
    "PostgreSQLDialect",
    "QueryGenerationError",
    "QueryGenerationResult",
    "QueryTarget",
    "SQLDDLImporter",
    "SQLDialect",
    "SQLGenerationError",
    "SQLGenerationOptions",
    "SQLGenerator",
    "SQLQueryGenerator",
    "SQLTarget",
    "SQLValidationIssue",
    "SQLValidationReport",
    "SQLValidationSeverity",
    "SQLiteDialect",
    "SubmodelResolver",
    "SubmodelScope",
    "TestDataGenerationError",
    "TestDataGenerationResult",
    "TestDataGenerator",
    "TestDataIssue",
    "VersionChange",
    "VersionComparison",
    "compare_models",
    "mcd_logical_fingerprint",
    "render_mld_text",
    "sql_dialect",
]
