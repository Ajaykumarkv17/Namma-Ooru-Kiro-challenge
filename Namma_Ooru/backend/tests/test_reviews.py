"""Example-based unit and API tests for review task 7.1 and 7.2."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.catalog.models import Destination
from app.catalog.repository import JsonDestinationRepository
from app.dependencies import get_review_service
from app.main import create_app
from app.reviews.models import Review, ReviewCreateRequest
from app.reviews.repository import InMemoryReviewRepository
from app.reviews.service import ReviewService, calculate_aggregate

DESTINATION_ID = "madurai-meenakshi-temple"


def _destination(**overrides: Any) -> Destination:
    data: dict[str, Any] = {
        "id": DESTINATION_ID,
        "name": "Meenakshi Temple",
        "city": "Madurai",
        "district": "madurai",
        "region": "South Tamil Nadu",
        "category": "temples",
        "description": "A test destination.",
        "source_urls": ["https://www.tamilnadutourism.tn.gov.in/"],
    }
    data.update(overrides)
    return Destination.model_validate(data)


def _service() -> ReviewService:
    return ReviewService(
        JsonDestinationRepository(destinations=[_destination()]),
        InMemoryReviewRepository(),
        clock=lambda: datetime(2025, 1, 1, tzinfo=UTC),
        id_factory=lambda: UUID("00000000-0000-0000-0000-000000000001"),
    )


def _client() -> TestClient:
    app = create_app()
    service = _service()
    app.dependency_overrides[get_review_service] = lambda: service
    return TestClient(app)


def test_create_persists_valid_review_with_destination_and_rating() -> None:
    service = _service()
    review = service.create(DESTINATION_ID, ReviewCreateRequest(rating=5, text="Wonderful visit."))

    assert review.destination_id == DESTINATION_ID
    assert review.rating == 5
    assert review.text == "Wonderful visit."
    assert service.get_aggregate(DESTINATION_ID).review_count == 1


def test_create_rejects_unknown_destination_without_persisting() -> None:
    service = _service()

    with pytest.raises(Exception, match="No destination exists"):
        service.create("unknown-place", ReviewCreateRequest(rating=4))

    assert service.get_aggregate(DESTINATION_ID).review_count == 0


def test_calculate_aggregate_reports_mean_histogram_and_newest_first_reviews() -> None:
    first = datetime(2025, 1, 1, tzinfo=UTC)
    reviews = [
        Review(
            id=UUID("00000000-0000-0000-0000-000000000001"),
            destination_id=DESTINATION_ID,
            rating=5,
            created_at=first,
        ),
        Review(
            id=UUID("00000000-0000-0000-0000-000000000002"),
            destination_id=DESTINATION_ID,
            rating=3,
            created_at=first + timedelta(days=1),
        ),
    ]

    aggregate = calculate_aggregate(DESTINATION_ID, reviews)

    assert aggregate.review_count == 2
    assert aggregate.average_rating == 4.0
    assert aggregate.rating_distribution == {1: 0, 2: 0, 3: 1, 4: 0, 5: 1}
    assert [review.rating for review in aggregate.reviews] == [3, 5]


def test_get_reviews_returns_empty_aggregate_for_existing_destination() -> None:
    response = _client().get(f"/api/destinations/{DESTINATION_ID}/reviews")

    assert response.status_code == 200
    assert response.json() == {
        "destination_id": DESTINATION_ID,
        "review_count": 0,
        "average_rating": None,
        "rating_distribution": {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0},
        "reviews": [],
        "ai_summary": None,
    }


def test_post_review_then_get_aggregate_returns_persisted_review() -> None:
    client = _client()
    created = client.post(
        f"/api/destinations/{DESTINATION_ID}/reviews",
        json={"rating": 4, "text": "Lovely architecture.", "tags": ["heritage"]},
    )

    assert created.status_code == 201
    assert created.json()["rating"] == 4
    response = client.get(f"/api/destinations/{DESTINATION_ID}/reviews")
    body = response.json()
    assert response.status_code == 200
    assert body["review_count"] == 1
    assert body["average_rating"] == 4.0
    assert body["rating_distribution"]["4"] == 1
    assert body["reviews"][0]["text"] == "Lovely architecture."


def test_get_reviews_adds_labelled_ai_summary_when_threshold_is_met() -> None:
    client = _client()
    client.post(f"/api/destinations/{DESTINATION_ID}/reviews", json={"rating": 5})
    client.post(f"/api/destinations/{DESTINATION_ID}/reviews", json={"rating": 2})

    body = client.get(f"/api/destinations/{DESTINATION_ID}/reviews").json()

    assert body["ai_summary"] == {
        "positives": ["1 review(s) gave a positive rating."],
        "concerns": ["1 review(s) noted a lower rating."],
        "review_count": 2,
    }


@pytest.mark.parametrize("rating", [0, 6, 3.5, "5"])
def test_post_rejects_out_of_range_or_non_integer_rating(rating: object) -> None:
    response = _client().post(
        f"/api/destinations/{DESTINATION_ID}/reviews", json={"rating": rating}
    )

    assert response.status_code == 400
    assert response.json()["error"] == "VALIDATION_ERROR"


def test_post_rejects_unknown_destination() -> None:
    response = _client().post("/api/destinations/unknown-place/reviews", json={"rating": 5})

    assert response.status_code == 404
    assert response.json()["error"] == "DESTINATION_NOT_FOUND"
