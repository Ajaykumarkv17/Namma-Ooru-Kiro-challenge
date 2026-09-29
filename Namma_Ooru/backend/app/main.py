"""FastAPI application factory for Namma Ooru."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, FastAPI

from app.ai import AIProvider
from app.dependencies import get_ai_provider
from app.errors import register_exception_handlers
from app.models import ChatRequest, GroundedAnswer


def create_app() -> FastAPI:
    """Create an application with centralized error handling and injectable services."""
    app = FastAPI(title="Namma Ooru API", version="0.1.0")
    register_exception_handlers(app)

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
