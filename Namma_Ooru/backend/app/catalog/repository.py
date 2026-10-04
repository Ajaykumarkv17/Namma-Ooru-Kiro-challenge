"""Destination Repository: the catalog storage abstraction (Requirement 3.1).

Destination data is stored separately from frontend components and reached only
through this repository layer. Two implementations share one ``Protocol`` so the
storage backend is swappable without touching callers:

* ``JsonDestinationRepository`` loads ``data/destinations.json`` for local dev
  and tests.
* ``DynamoDbDestinationRepository`` is a DynamoDB-ready adapter with matching
  interface parity. It is a stub here: no live AWS call is implemented (that is
  wired later), but the surface exists so the JSON repo can be swapped for it.

Deterministic filtering (``list``) and city grouping (``city_view``) are built on
the pure ``app.catalog.filters`` core so the ordering logic stays testable and
Properties 1-3 can target it directly.
"""

from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Sequence
from pathlib import Path
from typing import Protocol, runtime_checkable

from app.catalog.filters import apply_filters
from app.catalog.models import (
    CitySection,
    CityView,
    Destination,
    DestinationDetail,
    SearchFilters,
)
from app.catalog.vocabularies import DestinationCategory

# The repositories define a method named ``list``, which shadows the builtin
# inside their class bodies. ``DestinationList`` gives return annotations an
# unambiguous name for a list of Destinations.
DestinationList = list[Destination]


@runtime_checkable
class DestinationRepository(Protocol):
    """Storage-agnostic catalog interface (design: DestinationRepository)."""

    def get_by_id(self, destination_id: str) -> Destination | None:
        """Return the Destination with ``destination_id`` or ``None``."""
        ...

    def list(self, filters: SearchFilters) -> list[Destination]:
        """Return every Destination satisfying every active filter."""
        ...

    def city_view(self, city: str) -> CityView:
        """Return the grouped city overview for ``city`` (Requirement 2.1)."""
        ...

    def detail(self, destination_id: str) -> DestinationDetail | None:
        """Return the Destination with its resolved nearby places, or ``None``."""
        ...


# Ordered city section definitions (Requirement 2.1): popular places, temples,
# heritage, food, nature/nearby, hidden gems. Each entry maps a section key/title
# to a predicate over a Destination. Sections with no matches are dropped in the
# assembled CityView so the UI never renders an empty header.


class _SectionPredicate(Protocol):
    def __call__(self, destination: Destination) -> bool: ...


def _is_popular(destination: Destination) -> bool:
    return destination.popularity.popularity_score >= 0.5


def _is_temple(destination: Destination) -> bool:
    return destination.category is DestinationCategory.TEMPLES


def _is_heritage(destination: Destination) -> bool:
    return (
        destination.is_heritage
        or destination.is_unesco
        or destination.category is DestinationCategory.HERITAGE
    )


def _is_food(destination: Destination) -> bool:
    return destination.category is DestinationCategory.FOOD


def _is_nature(destination: Destination) -> bool:
    return destination.nature_related or destination.category in {
        DestinationCategory.NATURE,
        DestinationCategory.HILLS,
        DestinationCategory.WATERFALLS,
        DestinationCategory.WILDLIFE,
        DestinationCategory.BEACHES,
    }


def _is_hidden_gem(destination: Destination) -> bool:
    return destination.is_hidden_gem or destination.category is DestinationCategory.HIDDEN_GEMS


_SECTION_DEFINITIONS: tuple[tuple[str, str, _SectionPredicate], ...] = (
    ("popular", "Popular Places", _is_popular),
    ("temples", "Temples", _is_temple),
    ("heritage", "Heritage", _is_heritage),
    ("food", "Food", _is_food),
    ("nature", "Nature & Nearby", _is_nature),
    ("hidden-gems", "Hidden Gems", _is_hidden_gem),
)


def build_city_view(city: str, destinations: Sequence[Destination]) -> CityView:
    """Assemble a ``CityView`` from the destinations already scoped to ``city``.

    Pure and deterministic: it groups the given records into the ordered city
    sections, dropping any section with no matches. ``district``/``region`` come
    from the first record (they are consistent within a city in the dataset).
    """
    if not destinations:
        return CityView(city=city, destination_count=0, sections=[])

    district = destinations[0].district
    region = destinations[0].region
    sections: list[CitySection] = []
    for key, title, predicate in _SECTION_DEFINITIONS:
        matched = [d for d in destinations if predicate(d)]
        if matched:
            sections.append(CitySection(key=key, title=title, destinations=matched))

    return CityView(
        city=destinations[0].city,
        district=district,
        region=region,
        destination_count=len(destinations),
        sections=sections,
    )


def resolve_nearby(destination: Destination, by_id: dict[str, Destination]) -> list[Destination]:
    """Resolve ``destination.nearby_place_ids`` to real records (Requirement 2.4).

    Ids are resolved in listed order; ids with no matching catalogued place and
    any self-reference are dropped so nearby navigation only links to
    destinations that actually exist.
    """
    resolved: list[Destination] = []
    for nearby_id in destination.nearby_place_ids:
        if nearby_id == destination.id:
            continue
        nearby = by_id.get(nearby_id)
        if nearby is not None:
            resolved.append(nearby)
    return resolved


class _InMemoryDestinationRepository:
    """Shared in-memory backing used by concrete repositories.

    Holds an immutable-by-convention list plus an id index. Filtering and
    grouping delegate to the pure core so behavior matches every backend.
    """

    def __init__(self, destinations: Sequence[Destination]) -> None:
        self._destinations: list[Destination] = list(destinations)
        self._by_id: dict[str, Destination] = {d.id: d for d in self._destinations}
        self._by_city: dict[str, list[Destination]] = defaultdict(list)
        for destination in self._destinations:
            self._by_city[destination.city.casefold()].append(destination)

    def get_by_id(self, destination_id: str) -> Destination | None:
        return self._by_id.get(destination_id)

    def list(self, filters: SearchFilters) -> list[Destination]:
        return apply_filters(self._destinations, filters)

    def city_view(self, city: str) -> CityView:
        matched = self._by_city.get(city.casefold(), [])
        return build_city_view(city, matched)

    def detail(self, destination_id: str) -> DestinationDetail | None:
        destination = self._by_id.get(destination_id)
        if destination is None:
            return None
        return DestinationDetail(
            destination=destination,
            nearby=resolve_nearby(destination, self._by_id),
        )

    @property
    def all(self) -> DestinationList:
        return list(self._destinations)


def _default_dataset_path() -> Path:
    """Locate the catalog in either the local checkout or Lambda asset.

    CDK bundles the application at the Lambda asset root alongside
    ``data/destinations.json``.  In a local checkout the dataset remains at the
    project root, one level above ``backend``.
    """
    application_root = Path(__file__).resolve().parents[2]
    packaged_dataset = application_root / "data" / "destinations.json"
    if packaged_dataset.is_file():
        return packaged_dataset
    return application_root.parent / "data" / "destinations.json"


def load_destinations(path: Path) -> list[Destination]:
    """Parse the dataset file into validated ``Destination`` models.

    Accepts either a top-level array or a ``{"destinations": [...]}`` object so
    the loader tolerates both dataset shapes. Parsing is delegated to Pydantic;
    the dataset validator (task 2.1) is the gate that guarantees the file is
    already clean before this loads it.
    """
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, dict):
        records = raw.get("destinations", [])
    else:
        records = raw
    if not isinstance(records, list):
        raise ValueError("Dataset must be a list or an object with a 'destinations' list.")
    return [Destination.model_validate(record) for record in records]


class JsonDestinationRepository:
    """JSON-file-backed repository for local development and tests.

    Loads the dataset once at construction and serves reads from memory. The
    file path is injectable so tests can point at fixtures; production code uses
    the default ``data/destinations.json`` path.
    """

    def __init__(
        self,
        dataset_path: Path | None = None,
        *,
        destinations: Sequence[Destination] | None = None,
    ) -> None:
        if destinations is not None:
            records = list(destinations)
        else:
            path = dataset_path or _default_dataset_path()
            records = load_destinations(path)
        self._store = _InMemoryDestinationRepository(records)

    def get_by_id(self, destination_id: str) -> Destination | None:
        return self._store.get_by_id(destination_id)

    def list(self, filters: SearchFilters) -> list[Destination]:
        return self._store.list(filters)

    def city_view(self, city: str) -> CityView:
        return self._store.city_view(city)

    def detail(self, destination_id: str) -> DestinationDetail | None:
        return self._store.detail(destination_id)

    @property
    def all(self) -> DestinationList:
        return self._store.all


class DynamoDbDestinationRepository:
    """DynamoDB-ready adapter with interface parity to the JSON repository.

    This is a deliberate stub: it defines the same surface as
    ``DestinationRepository`` so the JSON repo can be swapped for a DynamoDB
    backend without changing callers, but it performs no live AWS calls yet.
    The table name and (optional) client are captured so the concrete
    implementation added later has the wiring it needs. Each method raises
    ``NotImplementedError`` until that implementation lands.
    """

    def __init__(self, table_name: str, *, client: object | None = None) -> None:
        self._table_name = table_name
        self._client = client

    @property
    def table_name(self) -> str:
        return self._table_name

    def get_by_id(self, destination_id: str) -> Destination | None:
        raise NotImplementedError("DynamoDB repository is not yet implemented.")

    def list(self, filters: SearchFilters) -> list[Destination]:
        raise NotImplementedError("DynamoDB repository is not yet implemented.")

    def city_view(self, city: str) -> CityView:
        raise NotImplementedError("DynamoDB repository is not yet implemented.")

    def detail(self, destination_id: str) -> DestinationDetail | None:
        raise NotImplementedError("DynamoDB repository is not yet implemented.")
