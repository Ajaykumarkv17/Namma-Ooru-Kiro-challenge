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
PRIMARY_GENERATION_MODEL_ID_KEY = "namma-ooru:primaryGenerationModelId"
FALLBACK_GENERATION_MODEL_ID_KEY = "namma-ooru:fallbackGenerationModelId"
CORS_ALLOWED_ORIGINS_KEY = "namma-ooru:corsAllowedOrigins"
FRONTEND_ENABLED_KEY = "namma-ooru:frontendEnabled"
FRONTEND_BRANCH_KEY = "namma-ooru:frontendBranch"
FRONTEND_REPOSITORY_URL_KEY = "namma-ooru:frontendRepositoryUrl"

# Conservative defaults so ``cdk synth`` works even without an overriding context.
DEFAULT_APP_NAME = "namma-ooru"
DEFAULT_VECTOR_DIMENSION = 1024  # Titan Text Embeddings V2 default dimension.
DEFAULT_EMBEDDING_MODEL_ID = "amazon.titan-embed-text-v2:0"
DEFAULT_PRIMARY_GENERATION_MODEL_ID = "us.amazon.nova-pro-v1:0"
DEFAULT_FALLBACK_GENERATION_MODEL_ID = "global.amazon.nova-2-lite-v1:0"
DEFAULT_CORS_ALLOWED_ORIGINS = ("http://localhost:5173",)
DEFAULT_FRONTEND_ENABLED = False
DEFAULT_FRONTEND_BRANCH = "main"


@dataclass(frozen=True)
class NammaOoruConfig:
    """Resolved, immutable configuration for the Namma Ooru infrastructure."""

    app_name: str
    vector_dimension: int
    embedding_model_id: str
    primary_generation_model_id: str
    fallback_generation_model_id: str
    cors_allowed_origins: tuple[str, ...]
    frontend_enabled: bool
    frontend_branch: str
    frontend_repository_url: str | None

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
        primary_generation_model_id = (
            scope.node.try_get_context(PRIMARY_GENERATION_MODEL_ID_KEY)
            or DEFAULT_PRIMARY_GENERATION_MODEL_ID
        )
        fallback_generation_model_id = (
            scope.node.try_get_context(FALLBACK_GENERATION_MODEL_ID_KEY)
            or DEFAULT_FALLBACK_GENERATION_MODEL_ID
        )
        raw_cors_allowed_origins = scope.node.try_get_context(CORS_ALLOWED_ORIGINS_KEY)
        if raw_cors_allowed_origins is None:
            cors_allowed_origins = DEFAULT_CORS_ALLOWED_ORIGINS
        elif isinstance(raw_cors_allowed_origins, (list, tuple)) and all(
            isinstance(origin, str) and origin.strip() for origin in raw_cors_allowed_origins
        ):
            cors_allowed_origins = tuple(origin.strip() for origin in raw_cors_allowed_origins)
        else:
            raise ValueError(f"{CORS_ALLOWED_ORIGINS_KEY} must be a non-empty list of origins.")
        raw_frontend_enabled = scope.node.try_get_context(FRONTEND_ENABLED_KEY)
        if raw_frontend_enabled is None:
            frontend_enabled = DEFAULT_FRONTEND_ENABLED
        elif isinstance(raw_frontend_enabled, bool):
            frontend_enabled = raw_frontend_enabled
        else:
            raise ValueError(f"{FRONTEND_ENABLED_KEY} must be a boolean.")
        frontend_branch = scope.node.try_get_context(FRONTEND_BRANCH_KEY) or DEFAULT_FRONTEND_BRANCH
        if not isinstance(frontend_branch, str) or not frontend_branch.strip():
            raise ValueError(f"{FRONTEND_BRANCH_KEY} must be a non-empty string.")
        raw_frontend_repository_url = scope.node.try_get_context(FRONTEND_REPOSITORY_URL_KEY)
        if raw_frontend_repository_url is not None and (
            not isinstance(raw_frontend_repository_url, str)
            or not raw_frontend_repository_url.strip()
        ):
            raise ValueError(f"{FRONTEND_REPOSITORY_URL_KEY} must be a non-empty string when set.")
        return cls(
            app_name=str(app_name),
            vector_dimension=vector_dimension,
            embedding_model_id=str(embedding_model_id),
            primary_generation_model_id=str(primary_generation_model_id),
            fallback_generation_model_id=str(fallback_generation_model_id),
            cors_allowed_origins=cors_allowed_origins,
            frontend_enabled=frontend_enabled,
            frontend_branch=frontend_branch.strip(),
            frontend_repository_url=(
                raw_frontend_repository_url.strip()
                if raw_frontend_repository_url is not None
                else None
            ),
        )
