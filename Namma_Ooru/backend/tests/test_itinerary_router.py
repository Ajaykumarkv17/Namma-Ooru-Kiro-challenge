"""Endpoint contracts for AI-assisted, deterministic itinerary planning."""

from fastapi.testclient import TestClient

from app.ai import LocalMockAIProvider
from app.catalog.models import Destination
from app.catalog.repository import JsonDestinationRepository
from app.dependencies import get_ai_provider, get_destination_repository, get_itinerary_service
from app.itinerary.service import ItineraryService
from app.main import create_app


def _destination(
    destination_id: str, city: str = "Madurai", district: str = "madurai"
) -> Destination:
    return Destination.model_validate(
        {
            "id": destination_id,
            "name": destination_id.replace("-", " ").title(),
            "city": city,
            "district": district,
            "region": "South Tamil Nadu",
            "category": "temples",
            "description": "A source-attributed test destination.",
            "recommended_duration_minutes": 60,
            "source_urls": ["https://www.tamilnadutourism.tn.gov.in/"],
        }
    )


def _client() -> TestClient:
    app = create_app()
    repository = JsonDestinationRepository(
        destinations=[_destination("madurai-temple"), _destination("madurai-museum")]
    )
    app.dependency_overrides[get_ai_provider] = LocalMockAIProvider
    app.dependency_overrides[get_destination_repository] = lambda: repository
    app.dependency_overrides[get_itinerary_service] = ItineraryService
    return TestClient(app)


def test_create_itinerary_returns_requested_days_and_catalog_activities() -> None:
    """Requirements 6.1, 6.2, 6.3, 6.5: validated endpoint delegates to the core."""
    response = _client().post(
        "/api/itineraries",
        json={"destination_context": "Madurai temples", "day_count": 2, "allow_repeats": False},
    )
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["days"]) == 2
    assert {
        activity["destination_id"] for day in payload["days"] for activity in day["activities"]
    } <= {
        "madurai-temple",
        "madurai-museum",
    }


def test_edit_itinerary_parses_operation_and_returns_unchanged_on_invalid_result() -> None:
    """Requirements 7.1-7.4: the API returns a safe unchanged plan when needed."""
    client = _client()
    itinerary = client.post(
        "/api/itineraries",
        json={"destination_context": "Madurai", "day_count": 1},
    ).json()
    response = client.post(
        f"/api/itineraries/{itinerary['id']}/edits",
        json={"request": "add unknown-place"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["changed"] is False
    assert payload["itinerary"] == itinerary


def test_itinerary_request_rejects_invalid_day_count() -> None:
    """Requirement 11.1: invalid trip input fails at the API boundary."""
    response = _client().post(
        "/api/itineraries", json={"destination_context": "Madurai", "day_count": 0}
    )
    assert response.status_code == 400
    assert response.json()["error"] == "VALIDATION_ERROR"


def test_named_location_with_no_catalog_data_never_uses_another_city() -> None:
    """Regression: a Chennai request cannot silently schedule Madurai places."""
    response = _client().post(
        "/api/itineraries",
        json={"destination_context": "3-day Chennai temples and food trip", "day_count": 3},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["no_data_reason"]
    assert all(not day["activities"] for day in payload["days"])
