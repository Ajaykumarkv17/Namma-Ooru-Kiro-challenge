/**
 * Catalog API types mirroring the backend Pydantic models in
 * `backend/app/catalog/models.py`. Kept in the service layer (never hard-coded in
 * components) so destination data always flows through the API.
 */

/** The 12 accepted Destination category slugs (backend `DestinationCategory`). */
export type DestinationCategory =
  | 'temples'
  | 'heritage'
  | 'beaches'
  | 'hills'
  | 'waterfalls'
  | 'nature'
  | 'wildlife'
  | 'food'
  | 'culture'
  | 'adventure'
  | 'photography'
  | 'hidden-gems';

/** Discovery ranking signals kept separate from source-verified facts. */
export type PopularityMetadata = {
  popularity_score: number;
  rating_average: number | null;
  rating_count: number;
};

/** Provenance for a factual Destination record. */
export type SourceAttribution = {
  name: string;
  type: string;
  url: string;
  retrieved_on: string;
  notes: string | null;
};

/**
 * A catalogued Tamil Nadu place. Nullable factual fields hold `null` until a
 * source verifies them, so the UI renders "Information unavailable" rather than a
 * fabricated value.
 */
export type Destination = {
  id: string;
  name: string;
  alternate_names: string[];
  city: string;
  district: string;
  region: string;
  category: DestinationCategory;
  subcategory: string | null;
  description: string;
  detailed_description: string | null;
  historical_significance: string | null;
  cultural_significance: string | null;
  latitude: number | null;
  longitude: number | null;
  address: string | null;
  best_time_to_visit: string | null;
  recommended_duration_minutes: number | null;
  opening_hours: string | null;
  entry_fee: string | null;
  official_website: string | null;
  source_urls: string[];
  sources: SourceAttribution[];
  image_reference: string | null;
  tags: string[];
  nearby_place_ids: string[];
  is_hidden_gem: boolean;
  is_heritage: boolean;
  is_unesco: boolean;
  family_friendly: boolean;
  nature_related: boolean;
  adventure_related: boolean;
  popularity: PopularityMetadata;
};

/** A titled, grouped slice of a city's destinations. */
export type CitySection = {
  key: string;
  title: string;
  destinations: Destination[];
};

/** A Destination plus its resolved nearby places. */
export type DestinationDetail = {
  destination: Destination;
  nearby: Destination[];
};

/** A city overview plus its grouped Destination sections. */
export type CityView = {
  city: string;
  district: string | null;
  region: string | null;
  destination_count: number;
  sections: CitySection[];
};

/** Deterministic catalog filter selection (backend `SearchFilters`). */
export type DestinationFilters = {
  city?: string;
  district?: string;
  category?: DestinationCategory;
  tags?: string[];
  family_friendly?: boolean;
  hidden_gems?: boolean;
};

/**
 * A single plottable destination marker plus minimal preview fields (backend
 * `MapMarker`). Emitted only for destinations with verified coordinates, so
 * `latitude`/`longitude` are non-nullable here.
 */
export type MapMarker = {
  id: string;
  name: string;
  latitude: number;
  longitude: number;
  category: DestinationCategory;
  city: string;
  district: string;
  description: string;
  image_reference: string | null;
  is_hidden_gem: boolean;
};

/**
 * Active map filters (backend `MapFilters`) — the map-relevant subset of the
 * catalog filters. Every field is optional; an absent field imposes no
 * constraint.
 */
export type MapFilters = {
  city?: string;
  district?: string;
  category?: DestinationCategory;
  tags?: string[];
  family_friendly?: boolean;
  hidden_gems?: boolean;
};

/** Structured backend error payload `{ error, detail }`. */
export type ApiErrorBody = {
  error?: string;
  detail?: string;
};
