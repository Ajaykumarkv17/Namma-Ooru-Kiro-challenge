"""Environment-specific configuration resolved from CDK context.

No credentials are ever read here; AWS authentication is resolved through the
standard AWS credential chain (profile / SSO / IAM role). Only non-secret,
declarative configuration lives in CDK context (see ``cdk.json``).
"""

from __future__ import annotations

from dataclasses import dataclass

from constructs import Construct

# Context keys (namespaced so they never collide with CDK feature flags).
APP_NAME_KEY = "namma-ooru:appName"
VECTOR_DIMENSION_KEY = "namma-ooru:vectorDimension"
EMBEDDING_MODEL_ID_KEY = "namma-ooru:embeddingModelId"
KNOWLEDGE_BASE_MODEL_ID_KEY = "namma-ooru:knowledgeBaseModelId"

# Conservative defaults so ``cdk synth`` works even without an overriding context.
DEFAULT_APP_NAME = "namma-ooru"
DEFAULT_VECTOR_DIMENSION = 1024  # Titan Text Embeddings V2 default dimension.
DEFAULT_EMBEDDING_MODEL_ID = "amazon.titan-embed-text-v2:0"
DEFAULT_KNOWLEDGE_BASE_MODEL_ID = "anthropic.claude-3-sonnet-20240229-v1:0"


@dataclass(frozen=True)
class NammaOoruConfig:
    """Resolved, immutable configuration for the Namma Ooru infrastructure."""

    app_name: str
    vector_dimension: int
    embedding_model_id: str
    knowledge_base_model_id: str

    @classmethod
    def from_context(cls, scope: Construct) -> NammaOoruConfig:
        """Resolve configuration from CDK context with safe defaults."""
        app_name = scope.node.try_get_context(APP_NAME_KEY) or DEFAULT_APP_NAME
        raw_dimension = scope.node.try_get_context(VECTOR_DIMENSION_KEY)
        vector_dimension = (
            int(raw_dimension) if raw_dimension is not None else DEFAULT_VECTOR_DIMENSION
        )
        embedding_model_id = (
            scope.node.try_get_context(EMBEDDING_MODEL_ID_KEY) or DEFAULT_EMBEDDING_MODEL_ID
        )
        knowledge_base_model_id = (
            scope.node.try_get_context(KNOWLEDGE_BASE_MODEL_ID_KEY)
            or DEFAULT_KNOWLEDGE_BASE_MODEL_ID
        )
        return cls(
            app_name=str(app_name),
            vector_dimension=vector_dimension,
            embedding_model_id=str(embedding_model_id),
            knowledge_base_model_id=str(knowledge_base_model_id),
        )
