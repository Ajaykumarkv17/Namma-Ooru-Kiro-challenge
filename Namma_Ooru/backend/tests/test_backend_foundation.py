"""Focused API and provider tests for task 1.2."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.ai import UNAVAILABLE_ANSWER, LocalMockAIProvider
from app.dependencies import get_ai_provider, get_destination_repository
from app.errors import DependencyUnavailableError, DomainError
from app.main import create_app
from app.models import GroundedAnswer, RetrievalFilters, SearchIntent


def test_local_mock_extracts_deterministic_search_intent() -> None:
    provider = LocalMockAIProvider()

    intent = provider.extract_search_intent("Plan a Madurai temples trip")

    assert intent.location == "Madurai"
    assert intent.category == "Temples"
    assert intent.interests == ["temples"]


def test_local_mock_returns_unavailable_answer_without_sources() -> None:
    response = LocalMockAIProvider().answer("What is the entry fee?", RetrievalFilters())

    assert response == GroundedAnswer(answer=UNAVAILABLE_ANSWER, sources=[], unavailable=True)


def test_chat_rejects_blank_question_with_structured_validation_error() -> None:
    client = TestClient(create_app())

    response = client.post("/api/chat", json={"question": "   "})

    assert response.status_code == 400
    assert response.json()["error"] == "VALIDATION_ERROR"
    assert response.json()["detail"][0]["field"] == "body.question"


def test_chat_uses_injected_ai_provider_and_separates_sources() -> None:
    class StubProvider:
        def extract_search_intent(
            self, query: str
        ) -> SearchIntent:  # pragma: no cover - protocol completeness
            raise AssertionError(f"Unexpected search request: {query}")

        def answer(self, question: str, filters: RetrievalFilters) -> GroundedAnswer:
            assert question == "Tell me about heritage"
            assert filters.city == "Madurai"
            return GroundedAnswer(answer="Grounded result", unavailable=False)

    app = create_app()
    app.dependency_overrides[get_ai_provider] = lambda: StubProvider()
    client = TestClient(app)

    response = client.post(
        "/api/chat",
        json={"question": "Tell me about heritage", "filters": {"city": "Madurai"}},
    )

    assert response.status_code == 200
    assert response.json() == {
        "answer": "Grounded result",
        "sources": [],
        "unavailable": False,
    }


def test_catalog_uses_shipped_dataset_without_initializing_ai() -> None:
    def unavailable_ai() -> LocalMockAIProvider:
        raise AssertionError("Catalog endpoints must not initialize an AI provider.")

    get_destination_repository.cache_clear()
    app = create_app()
    app.dependency_overrides[get_ai_provider] = unavailable_ai
    try:
        response = TestClient(app).get("/api/destinations")
    finally:
        get_destination_repository.cache_clear()

    assert response.status_code == 200
    assert response.json()


def test_chat_preflight_allows_only_configured_local_origin(monkeypatch) -> None:
    monkeypatch.delenv("CORS_ALLOWED_ORIGINS", raising=False)
    client = TestClient(create_app())
    headers = {
        "Origin": "http://localhost:5173",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type",
    }

    allowed = client.options("/api/chat", headers=headers)
    rejected = client.options(
        "/api/chat",
        headers={**headers, "Origin": "http://localhost:3000"},
    )

    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert allowed.headers["access-control-allow-methods"] == "GET, POST"
    assert rejected.status_code == 400
    assert "access-control-allow-origin" not in rejected.headers


def test_expected_dependency_error_has_safe_structured_response() -> None:
    app = create_app()

    @app.get("/test/dependency-error")
    def dependency_error() -> None:
        raise DependencyUnavailableError()

    client = TestClient(app)

    response = client.get("/test/dependency-error")

    assert response.status_code == 503
    assert response.json() == {
        "error": "AI_UNAVAILABLE",
        "detail": "The requested service is temporarily unavailable.",
    }


def test_domain_error_uses_status_code_supported_by_pinned_starlette() -> None:
    """Prevent Lambda import failures from unavailable Starlette status aliases."""
    assert DomainError.status_code == 422
