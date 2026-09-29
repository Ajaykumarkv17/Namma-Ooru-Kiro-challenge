"""Controlled Tamil Nadu district, category, and coordinate vocabularies.

These vocabularies are the single source of truth for the values a Destination
record may use. The data validator and the Pydantic models both consult them so
the dataset stays consistent with the data steering rules (valid districts, valid
categories, valid coordinate ranges).
"""

from __future__ import annotations

from enum import Enum


class TamilNaduDistrict(str, Enum):
    """The 38 administrative districts of Tamil Nadu.

    Enumerating every district lets the validator reject records that reference a
    district that does not exist (Requirement 3.4). Values are lower-kebab-case
    slugs so they are stable in URLs, filters, and Knowledge Base metadata.
    """

    ARIYALUR = "ariyalur"
    CHENGALPATTU = "chengalpattu"
    CHENNAI = "chennai"
    COIMBATORE = "coimbatore"
    CUDDALORE = "cuddalore"
    DHARMAPURI = "dharmapuri"
    DINDIGUL = "dindigul"
    ERODE = "erode"
    KALLAKURICHI = "kallakurichi"
    KANCHIPURAM = "kanchipuram"
    KANYAKUMARI = "kanyakumari"
    KARUR = "karur"
    KRISHNAGIRI = "krishnagiri"
    MADURAI = "madurai"
    MAYILADUTHURAI = "mayiladuthurai"
    NAGAPATTINAM = "nagapattinam"
    NAMAKKAL = "namakkal"
    NILGIRIS = "nilgiris"
    PERAMBALUR = "perambalur"
    PUDUKKOTTAI = "pudukkottai"
    RAMANATHAPURAM = "ramanathapuram"
    RANIPET = "ranipet"
    SALEM = "salem"
    SIVAGANGA = "sivaganga"
    TENKASI = "tenkasi"
    THANJAVUR = "thanjavur"
    THENI = "theni"
    THOOTHUKUDI = "thoothukudi"
    TIRUCHIRAPPALLI = "tiruchirappalli"
    TIRUNELVELI = "tirunelveli"
    TIRUPATHUR = "tirupathur"
    TIRUPPUR = "tiruppur"
    TIRUVALLUR = "tiruvallur"
    TIRUVANNAMALAI = "tiruvannamalai"
    TIRUVARUR = "tiruvarur"
    VELLORE = "vellore"
    VILUPPURAM = "viluppuram"
    VIRUDHUNAGAR = "virudhunagar"


class DestinationCategory(str, Enum):
    """The 12 accepted Destination categories (Requirement 3.3).

    Values are lower-kebab-case slugs; the ``label`` helper returns the
    display name used in requirements and UI copy.
    """

    TEMPLES = "temples"
    HERITAGE = "heritage"
    BEACHES = "beaches"
    HILLS = "hills"
    WATERFALLS = "waterfalls"
    NATURE = "nature"
    WILDLIFE = "wildlife"
    FOOD = "food"
    CULTURE = "culture"
    ADVENTURE = "adventure"
    PHOTOGRAPHY = "photography"
    HIDDEN_GEMS = "hidden-gems"

    @property
    def label(self) -> str:
        """Human-readable category label as written in the requirements."""
        return _CATEGORY_LABELS[self]


_CATEGORY_LABELS: dict[DestinationCategory, str] = {
    DestinationCategory.TEMPLES: "Temples",
    DestinationCategory.HERITAGE: "Heritage",
    DestinationCategory.BEACHES: "Beaches",
    DestinationCategory.HILLS: "Hills",
    DestinationCategory.WATERFALLS: "Waterfalls",
    DestinationCategory.NATURE: "Nature",
    DestinationCategory.WILDLIFE: "Wildlife",
    DestinationCategory.FOOD: "Food",
    DestinationCategory.CULTURE: "Culture",
    DestinationCategory.ADVENTURE: "Adventure",
    DestinationCategory.PHOTOGRAPHY: "Photography",
    DestinationCategory.HIDDEN_GEMS: "Hidden Gems",
}


# Tamil Nadu's geographic bounding box, padded slightly beyond the state borders
# so verified coordinates near the coast and hills are accepted while clearly
# out-of-state coordinates (Requirement 3.4: invalid coordinates) are rejected.
TN_LATITUDE_MIN = 8.0
TN_LATITUDE_MAX = 13.6
TN_LONGITUDE_MIN = 76.0
TN_LONGITUDE_MAX = 80.5


DISTRICT_SLUGS: frozenset[str] = frozenset(district.value for district in TamilNaduDistrict)
CATEGORY_SLUGS: frozenset[str] = frozenset(category.value for category in DestinationCategory)


def is_valid_district(value: str) -> bool:
    """Return True when ``value`` is one of the 38 Tamil Nadu district slugs."""
    return value in DISTRICT_SLUGS


def is_valid_category(value: str) -> bool:
    """Return True when ``value`` is one of the 12 accepted category slugs."""
    return value in CATEGORY_SLUGS


def is_valid_latitude(value: float) -> bool:
    """Return True when ``value`` falls within Tamil Nadu's latitude bounds."""
    return TN_LATITUDE_MIN <= value <= TN_LATITUDE_MAX


def is_valid_longitude(value: float) -> bool:
    """Return True when ``value`` falls within Tamil Nadu's longitude bounds."""
    return TN_LONGITUDE_MIN <= value <= TN_LONGITUDE_MAX
