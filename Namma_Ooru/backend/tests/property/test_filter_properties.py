"""Property-based tests for the pure deterministic filter core (tasks 2.4-2.6).

These tests target only ``app.catalog.filters.apply_filters`` and the
``SearchFilters`` / ``Destination`` Pydantic models. They build catalogs and
filter sets entirely in memory with Hypothesis strategies: no Bedrock, no AWS,
no network, and no live repository is touched, keeping the deterministic core
under test in isolation (architecture + testing steering).

Design property traceability (see ``.kiro/specs/namma-ooru/design.md`` ->
``## Correctness Properties``):

* Property 1 - Filter intersection soundness  -> ``test_property_1_...`` (Req 4.4)
* Property 2 - Filter removal preservation     -> ``test_property_2_...`` (Req 4.5)
* Property 3 - Filter monotonicity             -> ``test_property_3_...`` (Req 4.4)

Every test carries the ``property`` marker (declared in ``pyproject.toml``) and a
docstring naming its design property id and the requirement clause it validates.
Each test runs at least 100 generated examples per the testing steering.
"""

from __future__ import annotations

import dataclasses
from typing import Any

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from app.catalog.filters import apply_filters, matches
from app.catalog.models import Destination, SearchFilters
from app.catalog.vocabularies import DestinationCategory, TamilNaduDistrict

# At least 100 examples per property (testing steering). Set explicitly on each
# test so the requirement holds regardless of which Hypothesis profile is
# loaded; this mirrors ``[tool.hypothesis] max_examples = 100`` in pyproject.
PROPERTY_SETTINGS = settings(
    max_examples=100,
    deadline=None,
    # Building schema-valid Destination models makes each example moderately
    # large; that is inherent to exercising the real models (not a shrink
    # problem), so these size/timing health checks are suppressed. The property
    # logic itself is unaffected.
    suppress_health_check=[
        HealthCheck.too_slow,
        HealthCheck.large_base_example,
        HealthCheck.data_too_large,
    ],
)

# Small, closed value pools. Keeping the pools small makes it likely that a
# generated filter value actually matches some destination in the generated
# catalog, so the properties exercise non-empty result sets rather than trivially
# empty ones. Filter values are drawn from these same pools (see below), so any
# match a filter could produce is reachable.
_CITIES = ["Madurai", "Chennai", "Ooty", "Thanjavur"]
# Include mixed case to exercise the case-insensitive city match in the core.
_CITY_FILTER_VALUES = ["madurai", "MADURAI", "chennai", "Ooty", "thanjavur"]
_DISTRICTS = [
    TamilNaduDistrict.MADURAI,
    TamilNaduDistrict.CHENNAI,
    TamilNaduDistrict.NILGIRIS,
    TamilNaduDistrict.THANJAVUR,
]
_CATEGORIES = [
    DestinationCategory.TEMPLES,
    DestinationCategory.FOOD,
    DestinationCategory.HERITAGE,
    DestinationCategory.NATURE,
]
_TAGS = ["temple", "heritage", "food", "quiet", "family", "hills"]
# Mixed-case tag filter values exercise the case-insensitive tag intersection.
_TAG_FILTER_VALUES = ["temple", "HERITAGE", "Food", "quiet", "FAMILY", "Hills"]


def _make_destination(
    index: int,
    *,
    city: str,
    district: TamilNaduDistrict,
    category: DestinationCategory,
    tags: list[str],
    family_friendly: bool,
    is_hidden_gem: bool,
) -> Destination:
    """Build a schema-valid Destination from generated primitives.

    Only the fields the filter core reads (city, district, category, tags,
    family_friendly, is_hidden_gem) vary; everything else is a constant valid
    value so the model validates. The id is a unique slug per catalog index.
    """
    return Destination.model_validate(
        {
            "id": f"dest-{index}",
            "name": f"Destination {index}",
            "city": city,
            "district": district.value,
            "region": "Tamil Nadu",
            "category": category.value,
            "description": f"Generated destination {index}.",
            "tags": tags,
            "family_friendly": family_friendly,
            "is_hidden_gem": is_hidden_gem,
            "source_urls": ["https://www.tamilnadutourism.tn.gov.in/"],
        }
    )


@st.composite
def destinations(draw: st.DrawFn) -> Destination:
    """A single valid Destination drawn from the closed value pools."""
    index = draw(st.integers(min_value=0, max_value=1_000_000))
    return _make_destination(
        index,
        city=draw(st.sampled_from(_CITIES)),
        district=draw(st.sampled_from(_DISTRICTS)),
        category=draw(st.sampled_from(_CATEGORIES)),
        tags=draw(st.lists(st.sampled_from(_TAGS), max_size=len(_TAGS), unique=True)),
        family_friendly=draw(st.booleans()),
        is_hidden_gem=draw(st.booleans()),
    )


@st.composite
def catalogs(draw: st.DrawFn) -> list[Destination]:
    """A catalog (possibly empty) of Destinations with unique ids.

    Ids are re-assigned by position so two independently drawn destinations can
    never collide, keeping every catalog schema-valid.
    """
    base = draw(st.lists(destinations(), min_size=0, max_size=12))
    return [
        _make_destination(
            position,
            city=d.city,
            district=d.district,
            category=d.category,
            tags=list(d.tags),
            family_friendly=d.family_friendly,
            is_hidden_gem=d.is_hidden_gem,
        )
        for position, d in enumerate(base)
    ]


@st.composite
def search_filters(draw: st.DrawFn, *, require_active: bool = False) -> SearchFilters:
    """A SearchFilters drawing values from the same pools as the catalog.

    Each optional field is independently either unset or drawn from its pool, so
    filters range from empty (no constraint) to fully constrained. When
    ``require_active`` is true the draw is repeated until at least one constraint
    is present, which the intersection-soundness property needs (non-empty set of
    active filters).
    """
    while True:
        kwargs: dict[str, Any] = {}
        if draw(st.booleans()):
            kwargs["city"] = draw(st.sampled_from(_CITY_FILTER_VALUES))
        if draw(st.booleans()):
            kwargs["district"] = draw(st.sampled_from(_DISTRICTS))
        if draw(st.booleans()):
            kwargs["category"] = draw(st.sampled_from(_CATEGORIES))
        if draw(st.booleans()):
            kwargs["family_friendly"] = draw(st.booleans())
        if draw(st.booleans()):
            kwargs["hidden_gems"] = draw(st.booleans())
        tags = draw(st.lists(st.sampled_from(_TAG_FILTER_VALUES), max_size=3, unique=True))
        if tags:
            kwargs["tags"] = tags
        filters = SearchFilters(**kwargs)
        if not require_active:
            return filters
        # Retry until the filter imposes at least one constraint.
        if (
            any(
                v is not None
                for v in (
                    filters.city,
                    filters.district,
                    filters.category,
                    filters.family_friendly,
                    filters.hidden_gems,
                )
            )
            or filters.tags
        ):
            return filters


def _add_one_constraint(filters: SearchFilters, extra: SearchFilters) -> SearchFilters:
    """Return ``filters`` with exactly one additional constraint from ``extra``.

    Picks the first field that ``filters`` leaves unset and that ``extra``
    supplies a value for. Returns ``filters`` unchanged when no such field
    exists (the two filters already cover the same fields), which is still a
    valid case for the monotonicity property (adding nothing cannot grow the
    result set).
    """
    updates: dict[str, Any] = {}
    if filters.city is None and extra.city is not None:
        updates["city"] = extra.city
    elif filters.district is None and extra.district is not None:
        updates["district"] = extra.district
    elif filters.category is None and extra.category is not None:
        updates["category"] = extra.category
    elif filters.family_friendly is None and extra.family_friendly is not None:
        updates["family_friendly"] = extra.family_friendly
    elif filters.hidden_gems is None and extra.hidden_gems is not None:
        updates["hidden_gems"] = extra.hidden_gems
    elif extra.tags:
        new_tags = list(filters.tags)
        for tag in extra.tags:
            if tag.casefold() not in {t.casefold() for t in new_tags}:
                new_tags.append(tag)
                break
        updates["tags"] = new_tags
    if not updates:
        return filters
    return filters.model_copy(update=updates)


def _drop_one_constraint(data: st.DataObject, filters: SearchFilters) -> SearchFilters:
    """Return ``filters`` with one active constraint removed (chosen by draw)."""
    active: list[str] = [
        field
        for field in ("city", "district", "category", "family_friendly", "hidden_gems")
        if getattr(filters, field) is not None
    ]
    if filters.tags:
        active.append("tags")
    target = data.draw(st.sampled_from(active))
    if target == "tags":
        # Drop a single tag rather than all tags.
        drop_index = data.draw(st.integers(min_value=0, max_value=len(filters.tags) - 1))
        remaining = [t for i, t in enumerate(filters.tags) if i != drop_index]
        return filters.model_copy(update={"tags": remaining})
    return filters.model_copy(update={target: None})


# --- Property 1: Filter intersection soundness (Req 4.4) ----------------------


@pytest.mark.property
@given(catalog=catalogs(), filters=search_filters(require_active=True))
@PROPERTY_SETTINGS
def test_property_1_filter_intersection_soundness(
    catalog: list[Destination], filters: SearchFilters
) -> None:
    """Property 1 (intersection soundness), Validates: Requirements 4.4.

    For any Destination Catalog and any non-empty set of active SearchFilters,
    every Destination returned by ``apply_filters`` satisfies every active
    filter.
    """
    results = apply_filters(catalog, filters)
    assert all(matches(d, filters) for d in results)


# --- Property 2: Filter removal preservation (Req 4.5) ------------------------


@pytest.mark.property
@given(catalog=catalogs(), data=st.data())
@PROPERTY_SETTINGS
def test_property_2_filter_removal_preservation(
    catalog: list[Destination], data: st.DataObject
) -> None:
    """Property 2 (removal preservation), Validates: Requirements 4.5.

    For any catalog, active filters, and one removed filter, every Destination
    returned after removal satisfies every filter that remains active.
    """
    filters = data.draw(search_filters(require_active=True))
    reduced = _drop_one_constraint(data, filters)
    results = apply_filters(catalog, reduced)
    # Every result must still satisfy the remaining (reduced) filter set.
    assert all(matches(d, reduced) for d in results)


# --- Property 3: Filter monotonicity (Req 4.4) --------------------------------


@pytest.mark.property
@given(catalog=catalogs(), base=search_filters(), extra=search_filters(require_active=True))
@PROPERTY_SETTINGS
def test_property_3_filter_monotonicity(
    catalog: list[Destination], base: SearchFilters, extra: SearchFilters
) -> None:
    """Property 3 (monotonicity), Validates: Requirements 4.4.

    For any catalog and any valid filter, adding that filter to an existing
    filter set never increases the result set.
    """
    tighter = _add_one_constraint(base, extra)
    before = apply_filters(catalog, base)
    after = apply_filters(catalog, tighter)
    # Adding a constraint can only keep or shrink the result set.
    assert len(after) <= len(before)
    # The tighter result must be a subset of the looser one (by id, order-free).
    before_ids = {d.id for d in before}
    assert {d.id for d in after}.issubset(before_ids)


# Guard against silent breakage of the model-shape assumption these strategies
# rely on: the filter core only reads these six fields.
def test_strategy_assumptions_document_filter_fields() -> None:
    field_names = set(SearchFilters.model_fields)
    assert field_names == {
        "city",
        "district",
        "category",
        "tags",
        "family_friendly",
        "hidden_gems",
    }
    # dataclasses import kept meaningful: assert Destination is a Pydantic model,
    # not a dataclass, so ``model_validate`` is the correct constructor.
    assert not dataclasses.is_dataclass(Destination)
