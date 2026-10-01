"""Example tests for task 8.3's grounded Bedrock chat provider.

Validates: Requirements 5.2, 5.3, 5.4, 11.3
"""

from __future__ import annotations

from collections.abc import Mapping
from time import sleep
from typing import cast

import pytest

from app.ai import UNAVAILABLE_ANSWER, BedrockAIProvider
from app.errors import DependencyUnavailableError
from app.models import RetrievalFilters


class FakeAgentRuntimeClient:
    def __init__(self, response: Mapping[str, object]) -> None:
        self.response = response
        self.requests: list[dict[str, object]] = []

    def retrieve(self, **kwargs: object) -> Mapping[str, object]:
        self.requests.append(kwargs)
        return self.response


class FakeRuntimeClient:
    def __init__(self, response: Mapping[str, object]) -> None:
        self.response = response
        self.requests: list[dict[str, object]] = []

    def converse(self, **kwargs: object) -> Mapping[str, object]:
        self.requests.append(kwargs)
        return self.response


def _provider(
    retrieval_response: Mapping[str, object], generation_response: Mapping[str, object]
) -> tuple[BedrockAIProvider, FakeAgentRuntimeClient, FakeRuntimeClient]:
    agent_client = FakeAgentRuntimeClient(retrieval_response)
    runtime_client = FakeRuntimeClient(generation_response)
    return (
        BedrockAIProvider(
            knowledge_base_id="kb-123",
            model_id="model-123",
            agent_runtime_client=agent_client,
            runtime_client=runtime_client,
        ),
        agent_client,
        runtime_client,
    )


def test_answer_retrieves_filtered_context_then_returns_separate_sources() -> None:
    provider, agent_client, runtime_client = _provider(
        {
            "retrievalResults": [
                {
                    "content": {
                        "text": (
                            "# Meenakshi Temple\nSource URL: "
                            "https://www.tamilnadutourism.tn.gov.in/meenakshi"
                        )
                    },
                    "metadata": {
                        "destination_id": "madurai-meenakshi-temple",
                        "name": "Meenakshi Temple",
                    },
                }
            ]
        },
        {"output": {"message": {"content": [{"text": "Grounded temple details."}]}}},
    )

    answer = provider.answer("Tell me about the temple", RetrievalFilters(city="Madurai"))

    assert answer.answer == "Grounded temple details."
    assert answer.unavailable is False
    assert answer.sources[0].destination_id == "madurai-meenakshi-temple"
    assert str(answer.sources[0].url) == "https://www.tamilnadutourism.tn.gov.in/meenakshi"
    request = agent_client.requests[0]
    assert request["knowledgeBaseId"] == "kb-123"
    retrieval_configuration = cast(dict[str, object], request["retrievalConfiguration"])
    vector_search = cast(dict[str, object], retrieval_configuration["vectorSearchConfiguration"])
    assert vector_search["filter"] == {"equals": {"key": "city", "value": "Madurai"}}
    messages = cast(list[dict[str, object]], runtime_client.requests[0]["messages"])
    content = cast(list[dict[str, object]], messages[0]["content"])
    prompt = cast(str, content[0]["text"])
    assert "Retrieved Namma Ooru travel data" in prompt
    assert "Meenakshi Temple" in prompt


def test_answer_returns_unavailable_without_calling_generation_when_retrieval_is_empty() -> None:
    provider, _, runtime_client = _provider({"retrievalResults": []}, {})

    answer = provider.answer("What is the entry fee?", RetrievalFilters())

    assert answer.answer == UNAVAILABLE_ANSWER
    assert answer.sources == []
    assert answer.unavailable is True
    assert runtime_client.requests == []


def test_answer_converts_bedrock_errors_to_safe_dependency_failure() -> None:
    class FailingAgentRuntimeClient:
        def retrieve(self, **kwargs: object) -> Mapping[str, object]:
            del kwargs
            raise RuntimeError("credential details must not be exposed")

    provider = BedrockAIProvider(
        knowledge_base_id="kb-123",
        model_id="model-123",
        agent_runtime_client=FailingAgentRuntimeClient(),
        runtime_client=FakeRuntimeClient({}),
    )

    with pytest.raises(DependencyUnavailableError) as error:
        provider.answer("Question", RetrievalFilters())

    assert error.value.detail == "The requested service is temporarily unavailable."


def test_answer_enforces_dependency_deadline() -> None:
    class SlowAgentRuntimeClient:
        def retrieve(self, **kwargs: object) -> Mapping[str, object]:
            del kwargs
            sleep(0.05)
            return {"retrievalResults": []}

    provider = BedrockAIProvider(
        knowledge_base_id="kb-123",
        model_id="model-123",
        agent_runtime_client=SlowAgentRuntimeClient(),
        runtime_client=FakeRuntimeClient({}),
        timeout_seconds=0.001,
    )

    with pytest.raises(DependencyUnavailableError):
        provider.answer("Question", RetrievalFilters())
