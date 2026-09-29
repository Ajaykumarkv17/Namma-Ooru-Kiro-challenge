"""FastAPI application factory for Namma Ooru."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, FastAPI

from app.ai import AIProvider
from app.catalog.router import router as catalog_router
from app.dependencies import get_ai_provider
from app.errors import register_exception_handlers
from app.map.router import router as map_router
from app.models import ChatRequest, GroundedAnswer
from app.recommendations.router import router as recommendations_router
from app.search.router import router as search_router


def create_app() -> FastAPI:
    """Create an application with centralized error handling and injectable services."""
    app = FastAPI(title="Namma Ooru API", version="0.1.0")
    register_exception_handlers(app)
    app.include_router(catalog_router)
    app.include_router(map_router)
    app.include_router(search_router)
    app.include_router(recommendations_router)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/api/chat", response_model=GroundedAnswer)
    def chat(
        request: ChatRequest,
        ai_provider: Annotated[AIProvider, Depends(get_ai_provider)],
    ) -> GroundedAnswer:
        return ai_provider.answer(request.question, request.filters)

    return app


app = create_app()
