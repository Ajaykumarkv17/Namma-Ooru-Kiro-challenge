# Namma Ooru Technical Design

## Overview
Namma Ooru is a responsive web application for discovering Tamil Nadu destinations and planning
trips. It combines a browsable, source-attributed Destination Catalog with AI-assisted search,
a grounded Bedrock chatbot, multi-day itinerary generation, conversational itinerary edits,
recommendations, map discovery, and reviews.

The design deliberately separates deterministic travel logic from generative AI. Catalog filtering,
itinerary validation and scheduling, review validation, and recommendation membership are pure or
in-memory business rules. Amazon Bedrock is responsible for retrieval, intent interpretation, and
narrative generation, but cannot bypass the deterministic rules. This division gives the product a
credible local-demo mode and makes the universal business rules suitable for property-based tests.

The first deployment path is: deploy the backend, configure a local frontend with the CloudFormation
API URL, validate the integration, then deploy the frontend with AWS Amplify Hosting. No AWS
credential is stored in source control.

## Architecture

```text
Browser
  │
  ├── React + TypeScript frontend (Vite during development; Amplify Hosting in production)
  │      ├── React Query API client
  │      ├── Map Provider abstraction (MapLibre first implementation)
  │      └── accessible discovery, itinerary, review, and chat components
  │
  ▼ HTTPS JSON
API Gateway HTTP API
  ▼
FastAPI application on AWS Lambda (Mangum)
  ├── Destination Repository ────── JSON data locally / DynamoDB adapter later
  ├── Deterministic domain services
  │      ├── FilterService
  │      ├── ItineraryService
  │      ├── ReviewService
  │      └── RecommendationService
  └── AI Provider
         ├── LocalMockAIProvider for development and automated tests
         └── BedrockAIProvider
                 └── Bedrock Knowledge Base
                       ├── S3 source documents and sidecar metadata
                       └── S3 Vectors vector bucket and index
```

### Deployment architecture
- `DataStack` owns the source-document S3 bucket and application data resources.
- `AiStack` owns the S3 Vectors bucket/index, Bedrock Knowledge Base, S3 data source, and scoped
  Knowledge Base roles.
- `BackendStack` owns the FastAPI Lambda, API Gateway HTTP API, execution role, CORS configuration,
  and backend API URL output.
- `FrontendStack` owns Amplify Hosting and consumes the backend API URL as deployment configuration.
- `MonitoringStack` owns CloudWatch log retention, alarms, and dashboard resources.

All infrastructure is AWS CDK v2 in Python. AWS CDK assertions and `cdk synth` validate
infrastructure; property-based tests do not test AWS resources or deployment configuration.

### RAG flow
1. The data pipeline validates and normalizes source-attributed Destination records.
2. `build_kb.py` emits one source document and one `.metadata.json` sidecar per Destination.
3. The S3 data source ingests documents into the Knowledge Base and stores vectors in S3 Vectors.
4. `BedrockAIProvider` retrieves the top matching chunks with metadata filters when the request
   contains district, category, or other supported filter values.
5. `BedrockAIProvider` generates an answer only from retrieved chunks; the API returns generated
   text and retrieved source references as separate fields.

S3 Vectors metadata uses filterable values for district, city, category, region, heritage, UNESCO,
and travel type. `AMAZON_BEDROCK_TEXT` is configured as non-filterable so retrieval metadata
remains usable within the filterable metadata allowance.

## Components and Interfaces

### Frontend components
| Component | Responsibility |
|---|---|
| `HomePage` | Renders discovery hero, catalog sections, search entry, and map entry point. |
| `DestinationPage` | Renders one Destination, source links, nearby places, reviews, and AI summary. |
| `CityPage` | Renders city-grouped catalog sections and discovery guidance. |
| `SearchPage` | Submits Travel Queries and renders structured, filterable results. |
| `ChatWidget` | Sends questions to the chatbot endpoint and renders source-linked Grounded Responses. |
| `ItineraryPlanner` | Collects trip constraints, displays an itinerary, and submits edit requests. |
| `MapView` | Uses `MapProvider` to render filterable markers and previews. |
| `ReviewPanel` | Submits reviews and renders aggregate ratings, reviews, and AI summaries. |

### Backend interfaces
```python
class DestinationRepository(Protocol):
    def get_by_id(self, destination_id: str) -> Destination | None: ...
    def list(self, filters: SearchFilters) -> list[Destination]: ...
    def city_view(self, city: str) -> CityView: ...

class AIProvider(Protocol):
    def extract_search_intent(self, query: str) -> SearchIntent: ...
    def answer(self, question: str, filters: RetrievalFilters) -> GroundedAnswer: ...
    def parse_itinerary_edit(self, request: str, itinerary: Itinerary) -> ItineraryOperation: ...
    def summarize_reviews(self, reviews: list[Review]) -> ReviewSummary: ...

class MapProvider(Protocol):
    def render(self, markers: list[MapMarker], filters: MapFilters) -> None: ...
```

`LocalMockAIProvider` implements deterministic fixtures for local development and tests.
`BedrockAIProvider` implements Bedrock retrieval and generation for deployed environments.
The router layer validates Pydantic request models, invokes a domain service, and maps known
failures to API errors. Domain services do not call HTTP, S3, Bedrock, or DynamoDB directly.

### API contracts
| Method | Path | Request | Response |
|---|---|---|---|
| GET | `/api/destinations` | `SearchFilters` query parameters | `Destination[]` |
| GET | `/api/destinations/{id}` | destination id | `DestinationDetail` |
| GET | `/api/cities/{city}` | city slug | `CityView` |
| POST | `/api/search` | `TravelQueryRequest` | `SearchResult` |
| POST | `/api/chat` | `ChatRequest` | `GroundedAnswer` |
| POST | `/api/itineraries` | `ItineraryRequest` | `Itinerary` |
| POST | `/api/itineraries/{id}/edits` | `ItineraryEditRequest` | `Itinerary` or `EditUnavailable` |
| GET/POST | `/api/destinations/{id}/reviews` | Review query / `ReviewCreateRequest` | review data |
| POST | `/api/recommendations` | `RecommendationRequest` | `RecommendationResult` |
| GET | `/api/map/markers` | `MapFilters` query parameters | `MapMarker[]` |

## Data Models

### Destination
```text
Destination {
  id: DestinationId                         # unique lower-kebab-case slug
  name: string
  alternate_names: string[]
  city: string
  district: TamilNaduDistrict
  region: string
  category: DestinationCategory
  subcategory: string | null
  description: string
  detailed_description: string | null
  historical_significance: string | null
  cultural_significance: string | null
  latitude: decimal | null
  longitude: decimal | null
  address: string | null
  best_time_to_visit: string | null
  recommended_duration_minutes: integer | null
  opening_hours: string | null              # dynamic; source-verification date retained
  entry_fee: string | null                  # dynamic; source-verification date retained
  official_website: URL | null
  source_urls: URL[]
  sources: SourceAttribution[]
  image_reference: string | null
  tags: string[]
  nearby_place_ids: DestinationId[]
  is_hidden_gem: boolean
  is_heritage: boolean
  is_unesco: boolean
  family_friendly: boolean
  nature_related: boolean
  adventure_related: boolean
  popularity: PopularityMetadata
}
```

`SourceAttribution` contains `name`, `type`, `url`, `retrieved_on`, and `notes`. Dynamic source
values are represented as nullable data plus their source reference; the UI does not present them
as guaranteed current information.

### Search, itinerary, and review models
```text
SearchFilters { city?, district?, category?, tags[], family_friendly?, hidden_gems? }
SearchIntent { location?, duration_days?, category?, interests[], travel_style?, budget?, group_context? }
GroundedAnswer { answer: string, sources: RetrievedSource[], unavailable: boolean }

Itinerary {
  id: UUID
  destination_context: string
  days: ItineraryDay[]
  allow_repeats: boolean
}
ItineraryDay { day_number: positive integer, activities: ItineraryActivity[] }
ItineraryActivity {
  destination_id: DestinationId
  start_minute: integer from 0 through 1439
  duration_minutes: positive integer
  rationale: string
  travel_context: string
  break_suggestion: string
}
ItineraryOperation = Add | Remove | Replace | Reorder | Constrain

Review { id: UUID, destination_id: DestinationId, rating: integer 1..5, text: string?, tags: string[], created_at: ISO-8601 }
ReviewSummary { positives: string[], concerns: string[], review_count: positive integer }
```

### Knowledge Base documents
Each `data/kb/<destination-id>.md` contains a grounded Destination narrative and source URLs.
Each matching `data/kb/<destination-id>.md.metadata.json` stores district, city, category,
subcategory, region, heritage, UNESCO, and travel-type metadata. The data pipeline emits these
only after the dataset validator succeeds.

## Correctness Properties
*A property is a characteristic that holds across all valid executions. The following properties
test only Namma Ooru’s deterministic logic or in-memory adapters. Bedrock, S3, S3 Vectors,
API Gateway, AWS CDK, and UI layout use mocks, example-based tests, CDK assertions, smoke tests,
or visual tests rather than property-based tests.*

### Property 1: Filter intersection soundness
For any Destination Catalog and any non-empty set of active Search Filters, every Destination
returned by `FilterService.apply` satisfies every active Search Filter.
**Validates: Requirements 4.4**

### Property 2: Filter removal preservation
For any Destination Catalog, active Search Filters, and one removed Search Filter, every
Destination returned after removal satisfies every Search Filter that remains active.
**Validates: Requirements 4.5**

### Property 3: Filter monotonicity
For any Destination Catalog and any valid Search Filter, applying that Search Filter to an existing
filter set never increases the result set.
**Validates: Requirements 4.4**

### Property 4: Itinerary day-count preservation
For any valid Itinerary request with a requested day count from 1 through 14 and a sufficient
Destination Catalog, `ItineraryService.generate` returns exactly the requested number of day plans.
**Validates: Requirements 6.1**

### Property 5: Itinerary catalog-reference validity
For any valid Itinerary generated from a Destination Catalog, every Itinerary Activity destination
identifier exists in that Destination Catalog.
**Validates: Requirements 6.2**

### Property 6: Itinerary temporal validity
For any valid Itinerary generated by `ItineraryService`, every activity has a positive duration and
each day’s activities are ordered without temporal overlap.
**Validates: Requirements 6.2, 6.3**

### Property 7: Itinerary uniqueness when repeats are disabled
For any valid Itinerary request with `allow_repeats` set to false, no Destination identifier appears
more than once in the generated Itinerary.
**Validates: Requirements 6.5**

### Property 8: Edit invariant preservation
For any valid Itinerary and any successfully applied structured Itinerary Operation,
`ItineraryService.apply_operation` preserves valid catalog references, positive durations, and
non-overlapping activity ordering.
**Validates: Requirements 7.3**

### Property 9: Remove operation locality
For any valid Itinerary and removable activity, applying a Remove operation changes no activity
other than removal of the selected activity.
**Validates: Requirements 7.2**

### Property 10: Replace operation validity
For any valid Itinerary and a successful Replace operation, exactly one activity destination
identifier changes and the replacement identifier exists in the Destination Catalog.
**Validates: Requirements 7.1, 7.2**

### Property 11: Recommendation catalog membership
For any valid interest selection, themed journey, or Surprise Me request, every Destination returned
by `RecommendationService` exists in the Destination Catalog.
**Validates: Requirements 8.1, 8.2, 8.3, 8.4**

### Property 12: Map marker filter soundness
For any Destination Catalog and active Map Filters, every marker returned by `MapMarkerService`
references a Destination satisfying every active Map Filter and having verified coordinates.
**Validates: Requirements 9.1, 9.2**

### Property 13: Review acceptance boundary
For any existing Destination and integer rating from 1 through 5, `ReviewService.create` persists
a Review whose rating and Destination identifier equal the submitted values.
**Validates: Requirements 10.1**

### Property 14: Review rejection boundary
For any non-integer rating or integer rating outside 1 through 5, and for any unknown Destination
identifier, `ReviewService.create` rejects the request and leaves the Review store unchanged.
**Validates: Requirements 10.2**

### Property 15: Review aggregate consistency
For any non-empty collection of persisted Reviews for one Destination, the reported review count,
rating distribution total, and average rating equal the count, histogram total, and arithmetic mean
of that collection.
**Validates: Requirements 10.3**

## Error Handling
| Condition | Backend behavior | Frontend behavior |
|---|---|---|
| Invalid request model | Return `400 VALIDATION_ERROR` with field-safe details. | Display correction guidance. |
| Unknown Destination | Return `404 DESTINATION_NOT_FOUND`. | Display not-found state and discovery action. |
| Invalid review or itinerary operation | Return `422 BUSINESS_RULE_VIOLATION`. | Keep existing state and display actionable feedback. |
| Knowledge Base has no result | Return `200` GroundedAnswer with `unavailable=true` and no fabricated answer. | Display unavailable-information response. |
| Bedrock dependency failure | Return `503 AI_UNAVAILABLE`; use search fallback only where Requirement 4.3 applies. | Display retry action and non-AI browsing controls. |
| Repository or internal failure | Log correlation id; return `500 INTERNAL_ERROR` with safe message only. | Display retry state; do not render internal details. |

The FastAPI exception mapper is the sole place that translates domain exceptions into HTTP errors.
Prompt validation rejects malformed structured AI output before it reaches an itinerary or review
service. API Gateway integration timeout limits direct synchronous responses, so chat and itinerary
handlers use bounded retrieval and generation settings; the client receives a safe dependency error
when the bound is exceeded.

## Testing Strategy
- **Property-based tests:** Hypothesis runs at least 100 generated examples for each Property 1–15
  against pure domain services or in-memory repositories. Every test includes the feature/property
  tag and links to its design property.
- **Unit tests:** FastAPI request validation, structured-output parsing, known error mappings,
  source rendering, UI state transitions, and regression cases use concrete examples.
- **Integration tests:** FastAPI `TestClient` verifies endpoint contracts with `LocalMockAIProvider`.
  The browser test suite verifies the core discovery → detail → chat → itinerary → edit path.
- **Data validation tests:** JSON Schema validation and explicit dataset-validator tests verify
  required fields, allowed districts/categories, URLs, duplicate IDs/aliases, source attribution,
  and coordinate bounds. These are schema/example validation, not PBT.
- **Infrastructure tests:** `cdk synth`, AWS CDK assertions, IAM policy assertions, and a small
  deployed-backend smoke test validate the CDK stacks. These are not PBT because they test
  declarative infrastructure and external AWS behavior.
- **Accessibility tests:** automated semantic/keyboard/contrast checks plus manual screen-reader
  review before demo recording.
