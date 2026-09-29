"""Integration and unit tests for recommendations (task 4.3).

These exercise ``POST /api/recommendations`` with FastAPI's ``TestClient`` and a
fixture-backed ``JsonDestinationRepository`` injected via dependency override so
the tests never touch the shipped dataset. Coverage:

* interest matching by category and by tag (Requirement 8.1),
* each of the eight themed journeys returning matching catalog records
  (Requirement 8.3),
* Surprise Me returning exactly one catalog member with rationale, category,
  suggested duration, and short description (Requirement 8.2),
* catalog membership holding for every mode (Requirement 8.4),
* input-validation edge cases returning structured 400 errors (Requirement 11.1).

Also included are focused unit tests for the deterministic
``RecommendationService`` selection cores. Property 11 (catalog membership) is
covered separately by optional task 4.5 and is not written here.
"""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from app.catalog.models import Destination
from app.catalog.repository import JsonDestinationRepository
from app.catalog.vocabularies import DestinationCategory, TamilNaduDistrict
from app.dependencies import (
    get_destination_repository,
    get_recommendation_service,
)
from app.main import create_app
from app.recommendations.service import (
    RecommendationService,
    ThemedJourney,
    recommend_by_interests,
    recommend_by_journey,
    surprise_me,
)


def _destination(
    id_: str,
    *,
    city: str = "Madurai",
    district: TamilNaduDistrict = TamilNaduDistrict.MADURAI,
    category: DestinationCategory = DestinationCategory.TEMPLES,
    tags: list[str] | None = None,
    **overrides: Any,
) -> Destination:
    data: dict[str, Any] = {
        "id": id_,
        "name": id_.replace("-", " ").title(),
        "city": city,
        "district": district.value,
        "region": "South Tamil Nadu",
        "category": category.value,
        "description": f"Test destination {id_}.",
        "tags": tags or [],
        "source_urls": ["https://www.tamilnadutourism.tn.gov.in/"],
    }
    data.update(overrides)
    return Destination.model_validate(data)


def _catalog() -> list[Destination]:
    return [
        _destination(
            "madurai-meenakshi-temple",
            category=DestinationCategory.TEMPLES,
            tags=["temple", "heritage"],
            recommended_duration_minutes=120,
        ),
        _destination(
            "madurai-street-food-walk",
            category=DestinationCategory.FOOD,
            tags=["food", "evening"],
        ),
        _destination(
            "ooty-botanical-garden",
            city="Ooty",
            district=TamilNaduDistrict.NILGIRIS,
            category=DestinationCategory.HILLS,
            tags=["garden", "sunrise"],
            nature_related=True,
        ),
        _destination(
            "rameswaram-beach",
            city="Rameswaram",
            district=TamilNaduDistrict.RAMANATHAPURAM,
            category=DestinationCategory.BEACHES,
            tags=["beach", "sunrise"],
        ),
        _destination(
            "thanjavur-brihadeeswarar",
            city="Thanjavur",
            district=TamilNaduDistrict.THANJAVUR,
            category=DestinationCategory.HERITAGE,
            tags=["unesco"],
            is_unesco=True,
            is_heritage=True,
        ),
        _destination(
            "kutralam-falls",
            city="Tenkasi",
            district=TamilNaduDistrict.TENKASI,
            category=DestinationCategory.WATERFALLS,
            tags=["waterfall"],
        ),
        _destination(
            "photo-point-view",
            city="Kodaikanal",
            district=TamilNaduDistrict.DINDIGUL,
            category=DestinationCategory.PHOTOGRAPHY,
            tags=["viewpoint"],
        ),
        _destination(
            "hidden-village-trail",
            city="Yercaud",
            district=TamilNaduDistrict.SALEM,
            category=DestinationCategory.HIDDEN_GEMS,
            tags=["offbeat"],
            is_hidden_gem=True,
        ),
    ]


def _client() -> TestClient:
    app = create_app()
    repo = JsonDestinationRepository(destinations=_catalog())
    app.dependency_overrides[get_destination_repository] = lambda: repo
    app.dependency_overrides[get_recommendation_service] = lambda: RecommendationService()
    return TestClient(app)


# --- POST /api/recommendations: interests mode (Req 8.1) ----------------------


def test_interests_match_by_category() -> None:
    response = _client().post(
        "/api/recommendations", json={"mode": "interests", "interests": ["temple"]}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "interests"
    assert [d["id"] for d in body["destinations"]] == ["madurai-meenakshi-temple"]
    assert body["result_count"] == 1


def test_interests_match_by_tag() -> None:
    response = _client().post(
        "/api/recommendations", json={"mode": "interests", "interests": ["sunrise"]}
    )
    assert response.status_code == 200
    ids = [d["id"] for d in response.json()["destinations"]]
    assert ids == ["ooty-botanical-garden", "rameswaram-beach"]


def test_interests_union_across_multiple_interests() -> None:
    response = _client().post(
        "/api/recommendations", json={"mode": "interests", "interests": ["food", "beach"]}
    )
    assert response.status_code == 200
    ids = {d["id"] for d in response.json()["destinations"]}
    assert ids == {"madurai-street-food-walk", "rameswaram-beach"}


# --- POST /api/recommendations: themed journeys (Req 8.3) ---------------------


def test_each_themed_journey_returns_matching_records() -> None:
    client = _client()
    expected: dict[str, set[str]] = {
        "spiritual-journey": {"madurai-meenakshi-temple"},
        "hill-escape": {"ooty-botanical-garden", "kutralam-falls"},
        "coastal-escape": {"rameswaram-beach"},
        "food-trail": {"madurai-street-food-walk"},
        "heritage-journey": {"thanjavur-brihadeeswarar"},
        "nature-escape": {"ooty-botanical-garden", "kutralam-falls"},
        "photography-trip": {"photo-point-view"},
        "hidden-gems": {"hidden-village-trail"},
    }
    for journey, ids in expected.items():
        response = client.post("/api/recommendations", json={"mode": "journey", "journey": journey})
        assert response.status_code == 200, journey
        body = response.json()
        assert body["journey"] == journey
        assert {d["id"] for d in body["destinations"]} == ids, journey


# --- POST /api/recommendations: Surprise Me (Req 8.2) -------------------------


def test_surprise_returns_exactly_one_catalog_member_with_details() -> None:
    response = _client().post("/api/recommendations", json={"mode": "surprise"})
    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "surprise"
    assert body["result_count"] == 1
    assert len(body["destinations"]) == 1
    surprise = body["surprise"]
    assert surprise is not None
    catalog_ids = {d.id for d in _catalog()}
    assert surprise["destination"]["id"] in catalog_ids
    assert surprise["category"]
    assert surprise["short_description"]
    assert surprise["rationale"]
    assert surprise["rationale_is_ai_generated"] is True


def test_surprise_seed_selects_deterministically() -> None:
    catalog = _catalog()
    client = _client()
    response = client.post("/api/recommendations", json={"mode": "surprise", "seed": 3})
    assert response.status_code == 200
    surprise = response.json()["surprise"]
    assert surprise["destination"]["id"] == catalog[3].id
    assert surprise["suggested_duration_minutes"] == catalog[3].recommended_duration_minutes


# --- Catalog membership at the endpoint (Req 8.4) -----------------------------


def test_all_modes_return_only_catalog_members() -> None:
    client = _client()
    catalog_ids = {d.id for d in _catalog()}
    responses = [
        client.post("/api/recommendations", json={"mode": "interests", "interests": ["sunrise"]}),
        client.post("/api/recommendations", json={"mode": "journey", "journey": "nature-escape"}),
        client.post("/api/recommendations", json={"mode": "surprise", "seed": 5}),
    ]
    for response in responses:
        assert response.status_code == 200
        for destination in response.json()["destinations"]:
            assert destination["id"] in catalog_ids


# --- Input validation (Req 11.1) ----------------------------------------------


def test_interests_mode_requires_interests() -> None:
    response = _client().post("/api/recommendations", json={"mode": "interests", "interests": []})
    assert response.status_code == 400
    assert response.json()["error"] == "VALIDATION_ERROR"


def test_journey_mode_requires_journey() -> None:
    response = _client().post("/api/recommendations", json={"mode": "journey"})
    assert response.status_code == 400
    assert response.json()["error"] == "VALIDATION_ERROR"


def test_unknown_journey_rejected() -> None:
    response = _client().post(
        "/api/recommendations", json={"mode": "journey", "journey": "space-trip"}
    )
    assert response.status_code == 400
    assert response.json()["error"] == "VALIDATION_ERROR"


def test_unknown_mode_rejected() -> None:
    response = _client().post("/api/recommendations", json={"mode": "teleport"})
    assert response.status_code == 400
    assert response.json()["error"] == "VALIDATION_ERROR"


def test_unknown_fields_rejected() -> None:
    response = _client().post("/api/recommendations", json={"mode": "surprise", "unexpected": "x"})
    assert response.status_code == 400
    assert response.json()["error"] == "VALIDATION_ERROR"


def test_surprise_mode_rejects_interests() -> None:
    response = _client().post(
        "/api/recommendations", json={"mode": "surprise", "interests": ["food"]}
    )
    assert response.status_code == 400
    assert response.json()["error"] == "VALIDATION_ERROR"


def test_negative_seed_rejected() -> None:
    response = _client().post("/api/recommendations", json={"mode": "surprise", "seed": -1})
    assert response.status_code == 400
    assert response.json()["error"] == "VALIDATION_ERROR"


# --- Unit tests for the deterministic recommendation cores --------------------


def test_recommend_by_interests_matches_category_or_tag() -> None:
    catalog = _catalog()
    result = recommend_by_interests(catalog, ["heritage"])
    ids = {d.id for d in result}
    # "heritage" is a tag on the temple and a category on the Thanjavur record.
    assert ids == {"madurai-meenakshi-temple", "thanjavur-brihadeeswarar"}


def test_recommend_by_interests_empty_when_no_usable_interest() -> None:
    catalog = _catalog()
    assert recommend_by_interests(catalog, ["", "   "]) == []


def test_recommend_by_journey_uses_journey_predicate() -> None:
    catalog = _catalog()
    result = recommend_by_journey(catalog, ThemedJourney.COASTAL_ESCAPE)
    assert [d.id for d in result] == ["rameswaram-beach"]


def test_surprise_me_is_deterministic_for_seed() -> None:
    catalog = _catalog()
    first = surprise_me(catalog, seed=2)
    second = surprise_me(catalog, seed=2)
    assert first is not None and second is not None
    assert first.destination.id == second.destination.id == catalog[2].id


def test_surprise_me_none_for_empty_catalog() -> None:
    assert surprise_me([]) is None
