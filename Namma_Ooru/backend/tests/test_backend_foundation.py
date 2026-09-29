"""Focused API and provider tests for task 1.2."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.ai import UNAVAILABLE_ANSWER, LocalMockAIProvider
from app.dependencies import get_ai_provider
from app.errors import DependencyUnavailableError
from app.main import create_app
from app.models import GroundedAnswer, RetrievalFilters


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
        def extract_search_intent(self, query: str):  # pragma: no cover - protocol completeness
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
