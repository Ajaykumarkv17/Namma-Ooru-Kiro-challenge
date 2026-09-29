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

/**
 * AI-derived interpretation of a natural-language Travel Query (backend
 * `SearchIntent`). Every field is optional; this is the model's reading of the
 * query and is kept separate from source catalog data (AI/RAG steering) so the UI
 * can badge it as an interpretation rather than a fact.
 */
export type SearchIntent = {
  location: string | null;
  duration_days: number | null;
  category: string | null;
  interests: string[];
  travel_style: string | null;
  budget: string | null;
  group_context: string | null;
};

/**
 * Structured response for `POST /api/search` (backend `SearchResult`). Keeps the
 * AI-derived `intent`, the deterministic `filters` those mapped to, and the
 * retrieved `destinations` in separate fields. `used_fallback` is true when the
 * AI Provider was unavailable and deterministic keyword/tag matching was used
 * instead; `fallback_reason` is a short, client-safe explanation to surface
 * (Requirement 4.3).
 */
export type SearchResult = {
  query: string;
  intent: SearchIntent;
  filters: DestinationFilters;
  destinations: Destination[];
  result_count: number;
  used_fallback: boolean;
  fallback_reason: string | null;
};

/** Structured backend error payload `{ error, detail }`. */
export type ApiErrorBody = {
  error?: string;
  detail?: string;
};

/**
 * The eight named themed journeys (backend `ThemedJourney`). Slugs are the exact
 * wire values `POST /api/recommendations` accepts for `{ mode: "journey" }`
 * (Requirement 8.3).
 */
export type ThemedJourney =
  | 'spiritual-journey'
  | 'hill-escape'
  | 'coastal-escape'
  | 'food-trail'
  | 'heritage-journey'
  | 'nature-escape'
  | 'photography-trip'
  | 'hidden-gems';

/** The three recommendation modes (backend `RecommendationMode`). */
export type RecommendationMode = 'interests' | 'journey' | 'surprise';

/**
 * Validated recommendation input for `POST /api/recommendations` (backend
 * `RecommendationRequest`). Exactly one mode is expressed at a time:
 * - `interests` (Req 8.1): `interests` is required and non-empty.
 * - `journey` (Req 8.3): `journey` is one of the eight themed-journey slugs.
 * - `surprise` (Req 8.2): only the optional `seed` is used.
 * Cross-field consistency is validated at the backend boundary; an inconsistent
 * request is rejected with a structured `{ error: "VALIDATION_ERROR", detail }`
 * 400 (Requirement 11.1).
 */
export type RecommendationRequest =
  | { mode: 'interests'; interests: string[] }
  | { mode: 'journey'; journey: ThemedJourney }
  | { mode: 'surprise'; seed?: number };

/**
 * A single Surprise Me pick (backend `SurpriseRecommendation`). `destination` and
 * `category` are source catalog facts; `suggested_duration_minutes` and
 * `short_description` come from the record (never fabricated). `rationale` is
 * AI-generated prose — kept in its own field and flagged by
 * `rationale_is_ai_generated` so generated text is never conflated with source
 * facts (AI/RAG steering) and the UI can badge it as AI-generated.
 */
export type SurpriseRecommendation = {
  destination: Destination;
  category: DestinationCategory;
  suggested_duration_minutes: number | null;
  short_description: string;
  rationale: string;
  rationale_is_ai_generated: boolean;
};

/**
 * Structured recommendation response (backend `RecommendationResult`,
 * Requirements 8.1, 8.2, 8.3). `mode` echoes the request; `journey` is set for
 * journey mode. `destinations` holds the matching catalog records for
 * interests/journey modes; `surprise` holds the single pick for surprise mode.
 * Every returned Destination is a catalog member (Requirement 8.4).
 */
export type RecommendationResult = {
  mode: RecommendationMode;
  journey: ThemedJourney | null;
  interests: string[];
  destinations: Destination[];
  result_count: number;
  surprise: SurpriseRecommendation | null;
};
