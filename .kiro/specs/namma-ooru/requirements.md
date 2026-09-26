# Namma Ooru — Requirements

**Tagline:** Discover the Tamil Nadu you haven't seen.

Namma Ooru is an AI-powered Tamil Nadu travel discovery and trip-planning platform. This
document captures the testable requirements for the main feature spec. Requirements use the
EARS pattern (Easy Approach to Requirements Syntax) so each acceptance criterion is verifiable.

Legend for traceability tags:
- `[PBT]` — requirement has universal properties suitable for property-based testing (Lesson 4).
- `[AI]` — requirement depends on the AI/RAG layer (Bedrock).
- `[DATA]` — requirement depends on the researched destination dataset.

---

## Requirement 1 — Discover Tamil Nadu (Home Experience)

**User Story:** As a visitor, I want an attractive home experience that surfaces Tamil Nadu
destinations, so that I can start exploring without needing to use AI.

### Acceptance Criteria
1. WHEN a user opens the home page THEN the system SHALL render a hero section, a search bar, and an "Explore Tamil Nadu" call to action.
2. WHEN the home page loads THEN the system SHALL display sections for popular destinations, popular cities, categories, hidden gems, and recommended destinations. `[DATA]`
3. WHEN the home page loads THEN the system SHALL display an interactive Tamil Nadu map entry point.
4. WHILE destination data is loading THE system SHALL display skeleton loading states rather than blank areas.
5. IF a data section returns no results THEN the system SHALL display an empty state with guidance instead of an error.
6. WHEN a user browses the home page THEN the system SHALL allow navigation to any destination or city detail without invoking AI.

---

## Requirement 2 — Explore a City / District

**User Story:** As a traveler, I want a rich city page, so that I can understand what a place
offers before visiting.

### Acceptance Criteria
1. WHEN a user selects a city (e.g. Madurai) THEN the system SHALL display a hero image, city overview, and grouped sections for popular places, temples, heritage, food, and nature/nearby attractions. `[DATA]`
2. WHEN a city page renders THEN the system SHALL display hidden gems, average ratings, reviews, nearby destinations, suggested duration, best time to visit, and travel tips where data exists. `[DATA]`
3. IF a field is unavailable for a city or place THEN the system SHALL render "Information unavailable" rather than a fabricated value. `[DATA]`
4. WHEN the same navigation pattern is applied to any Tamil Nadu city with data THEN the system SHALL render the same section structure.

---

## Requirement 3 — Destination Catalog & Data Model

**User Story:** As a product owner, I want a structured, extensible destination model, so that
new categories and destinations can be added without code changes to components.

### Acceptance Criteria
1. THE system SHALL model each destination with at minimum: id, name, alternate_names, city, district, region, category, subcategory, description, detailed_description, historical_significance, cultural_significance, latitude, longitude, address, best_time_to_visit, recommended_duration, opening_hours, entry_fee, official_website, source_urls, image_reference, tags, nearby_places, is_hidden_gem, is_heritage, is_unesco, family_friendly, nature_related, adventure_related, average_rating, review_count, and popularity metadata. `[DATA] [PBT]`
2. THE system SHALL support at least these categories: Temples, Heritage, Beaches, Hills, Waterfalls, Nature, Wildlife, Food, Culture, Adventure, Photography, Hidden Gems. `[PBT]`
3. WHERE a destination field is uncertain or unavailable THE system SHALL store it as null rather than an invented value. `[DATA]`
4. THE system SHALL store destination data separately from frontend components (data files / API), not hard-coded inside UI components.
5. WHEN a destination is validated THEN it SHALL reference a valid district and a valid category. `[PBT] [DATA]`
6. THE system SHALL retain source attribution (source_urls, source name, source type, retrieval date) for every factual destination record. `[DATA]`

---

## Requirement 4 — AI Natural-Language Search

**User Story:** As a traveler, I want to search in natural language, so that I get relevant
destinations without knowing exact names or filters.

### Acceptance Criteria
1. WHEN a user submits a natural-language query THEN the system SHALL extract intent including location, duration, category, interests, travel style, budget, and group context where present. `[AI]`
2. WHEN a search completes THEN the system SHALL return structured destination results, not only plain text. `[AI] [DATA]`
3. WHEN filters are active THEN the search results SHALL only contain destinations satisfying every active filter. `[PBT]`
4. WHEN a filter is removed THEN the result set SHALL NOT contain destinations that violate a still-active filter. `[PBT]`
5. IF intent extraction fails or the model is unavailable THEN the system SHALL fall back to keyword/tag search and inform the user.
6. WHILE a search is running THE system SHALL show a loading state.

---

## Requirement 5 — Amazon Bedrock AI Chatbot (RAG)

**User Story:** As a traveler, I want an AI chatbot grounded in Namma Ooru knowledge, so that I
get reliable answers about Tamil Nadu travel.

### Acceptance Criteria
1. THE chatbot SHALL answer using a Retrieval-Augmented Generation pipeline over an Amazon Bedrock Knowledge Base backed by S3 (source) and S3 Vectors (vector store). `[AI]`
2. WHEN the chatbot answers THEN the response SHALL be grounded in retrieved knowledge, and the architecture SHALL keep retrieved context separate from generated text. `[AI]`
3. IF the knowledge base has no relevant content for a question THEN the chatbot SHALL say it does not have that information rather than fabricating facts. `[AI]`
4. THE chatbot SHALL be embedded and reachable from across the application.
5. THE system SHALL NOT store AWS credentials or secrets in source control.
6. WHEN a chatbot answer cites facts THEN it SHOULD reference the source destination(s) where available. `[AI] [DATA]`

---

## Requirement 6 — AI Itinerary Planner (Hero Feature)

**User Story:** As a traveler, I want an AI-generated multi-day itinerary, so that I can plan a
trip logically without manual research.

### Acceptance Criteria
1. WHEN a user provides a destination, number of days, budget, travel style, interests, starting point, and preferences THEN the system SHALL generate a day-by-day itinerary. `[AI] [DATA]`
2. THE generated itinerary for N days SHALL contain exactly N days. `[PBT]`
3. WHEN an itinerary is generated THEN each activity SHALL include time/order, place, approximate duration, why-to-visit, travel context, and a nearby food/break suggestion. `[AI]`
4. THE system SHALL order activities to reduce unnecessary travel, considering proximity, opening hours where known, recommended duration, interests, trip length, travel style, and budget. `[AI]`
5. EACH itinerary activity SHALL reference a valid, existing destination. `[PBT] [DATA]`
6. WITHIN a single itinerary no destination SHALL be duplicated unless explicitly allowed. `[PBT]`
7. EACH activity SHALL have a positive duration and valid, non-overlapping ordered times within a day. `[PBT]`

---

## Requirement 7 — Conversational Itinerary Editing

**User Story:** As a traveler, I want to modify an itinerary in natural language, so that I can
refine it without regenerating from scratch.

### Acceptance Criteria
1. WHEN a user issues an edit instruction (e.g. "remove the palace", "add one more temple", "make day 2 less crowded", "make the trip cheaper", "replace this place with something nearby") THEN the system SHALL apply only the requested change. `[AI]`
2. WHEN an edit is applied THEN the system SHALL preserve unaffected parts of the itinerary. `[PBT]`
3. AFTER an edit THE itinerary SHALL still satisfy all itinerary invariants in Requirement 6 (day count preserved unless the edit changes it, valid references, positive durations, valid ordering). `[PBT]`
4. IF an edit cannot be satisfied (e.g. no nearby alternative) THEN the system SHALL explain why and leave the itinerary unchanged.

---

## Requirement 8 — Personalized Discovery & Surprise Me

**User Story:** As a traveler, I want recommendations based on my interests, so that discovery
feels personal.

### Acceptance Criteria
1. WHEN a user selects interests (temples, history, food, nature, beaches, adventure, photography, culture, hidden gems) THEN the system SHALL recommend destinations matching those interests. `[DATA]`
2. WHEN a user clicks "Surprise Me" THEN the system SHALL recommend an unexpected destination with destination, why-it-matches, category, suggested duration, and short description. `[DATA]`
3. THE recommendations SHALL only include destinations present in the catalog. `[PBT] [DATA]`

---

## Requirement 9 — Creative Travel Discovery

**User Story:** As a traveler, I want themed journeys, so that I can explore by mood/intent.

### Acceptance Criteria
1. WHEN a user opens "What kind of journey are you looking for?" THEN the system SHALL present journey options: Spiritual, Hill Escape, Coastal Escape, Food Trail, Heritage, Nature Escape, Photography, Hidden Gems.
2. WHEN a user selects a journey THEN the system SHALL dynamically recommend matching destinations. `[DATA]`
3. THE system SHALL provide a "Beyond the Tourist Map" experience surfacing hidden/lesser-known destinations. `[DATA]`

---

## Requirement 10 — Interactive Tamil Nadu Map

**User Story:** As a traveler, I want a map-based discovery view, so that I can explore
destinations spatially.

### Acceptance Criteria
1. WHEN the map view loads THEN the system SHALL render destination markers using stored coordinates. `[DATA]`
2. WHEN a user filters by category or selects a city THEN the map SHALL only show markers matching the filter. `[PBT]`
3. WHEN a user clicks a marker THEN the system SHALL open a destination preview and allow navigation to the detail page.
4. THE map layer SHALL be replaceable (abstraction) so a lightweight implementation can be swapped for a production provider without changing feature logic.

---

## Requirement 11 — Reviews & Ratings

**User Story:** As a traveler, I want to read and submit reviews, so that I can judge and share
destination experiences.

### Acceptance Criteria
1. WHEN a user submits a review THEN the system SHALL accept a 1–5 star rating, review text, and optional tags. `[PBT]`
2. THE system SHALL reject any rating outside the 1–5 integer range and SHALL NOT persist it. `[PBT]`
3. EVERY review SHALL reference an existing destination. `[PBT] [DATA]`
4. WHEN a destination page renders THEN the system SHALL display average rating, rating distribution, review count, and recent reviews. `[PBT]`
5. WHERE a destination has enough reviews THE system SHALL display an AI-generated review summary listing frequently mentioned positives and common concerns. `[AI]`
6. THE system SHALL clearly label AI-generated summaries as distinct from individual user reviews. `[AI]`

---

## Requirement 12 — Visual Design & UX Quality

**User Story:** As a user, I want a premium, culturally-grounded travel UI, so that the product
feels modern and trustworthy.

### Acceptance Criteria
1. THE UI SHALL provide destination cards with large imagery, smooth transitions, modern typography, and a Tamil Nadu cultural identity.
2. THE UI SHALL be responsive and mobile-friendly with accessible navigation.
3. THE UI SHALL implement loading, empty, error, and skeleton states across data-driven sections.
4. THE UI SHALL meet accessibility basics: semantic markup, keyboard navigation, sufficient contrast, and alt text for imagery.
5. THE UI SHALL NOT resemble a generic admin dashboard.

---

## Requirement 13 — Data Acquisition, Research & Quality

**User Story:** As a product owner, I want a broad, reliable, source-attributed dataset, so that
the platform fulfills its tagline with trustworthy facts.

### Acceptance Criteria
1. THE dataset SHALL be built from multiple reliable sources, prioritizing official TN Tourism/TTDC, TN district portals, TN government departments (HR&CE for temples, Archaeology for monuments), and Incredible India, with other reputable sources only when necessary. `[DATA]`
2. THE dataset SHALL cover destinations across most Tamil Nadu districts, not only the most famous cities, and SHALL include a diverse range of categories (temples, heritage, UNESCO, forts, palaces, museums, beaches, hills, waterfalls, lakes, dams, wildlife, forests, bird sanctuaries, wetlands, caves, archaeological sites, churches, mosques, Jain heritage, cultural, food, adventure, photography, hidden gems, viewpoints, islands/coastal, family). `[DATA]`
3. THE data pipeline SHALL be repeatable: research → collection → extraction → normalization → deduplication → cross-source validation → schema validation → human-review flags → dataset → S3 KB data → Bedrock/S3 Vectors. `[DATA]`
4. THE system SHALL never invent opening hours, entry fees, coordinates, historical facts, temple info, distances, contact info, or accessibility info; unknown values SHALL remain null. `[DATA]`
5. WHERE sources conflict THE record SHALL be flagged for review and prefer the authoritative government source. `[DATA]`
6. THE dataset SHALL distinguish stable information from dynamic information (hours, fees, closures, access, weather, festivals) and link to official sources for verification. `[DATA]`

---

## Requirement 14 — Data Validation

**User Story:** As a maintainer, I want automated dataset validation, so that data quality is
enforced continuously.

### Acceptance Criteria
1. THE validator SHALL check required fields, valid district names, valid categories, valid coordinate ranges, duplicate places, duplicate aliases, invalid ratings, invalid relationships, missing source references, malformed URLs, incorrect district/category mappings, and empty descriptions. `[PBT] [DATA]`
2. WHEN validation fails THEN the process SHALL report the specific record and rule that failed with a non-zero exit code. `[DATA]`
3. THE validator SHALL run as a Kiro Hook on relevant data changes (Lesson 3). `[DATA]`

---

## Requirement 15 — AWS Infrastructure as Code (Python CDK)

**User Story:** As a maintainer, I want all AWS infrastructure defined in Python CDK v2, so that
the environment is reproducible and reviewable.

### Acceptance Criteria
1. ALL production AWS infrastructure SHALL be defined with AWS CDK v2 in Python (3.9+) under `infra/`, not created manually in the console where CDK can provision it.
2. THE infrastructure SHALL be split into logical stacks: frontend, backend, data, ai, monitoring.
3. THE IAM policies SHALL follow least privilege, and no credentials or secrets SHALL be committed.
4. THE CDK app SHALL support environment-specific configuration and expose useful CloudFormation outputs.
5. THE backend SHALL be deployable so it can be tested with a local frontend before the frontend is deployed to AWS Amplify.

---

## Requirement 16 — Security & Secrets

**User Story:** As a maintainer, I want secure defaults, so that credentials and inputs are safe.

### Acceptance Criteria
1. THE system SHALL keep AWS credentials and secrets out of source control (no committed `.env` with secrets).
2. THE backend SHALL validate and sanitize all user input before use in queries or prompts.
3. THE API SHALL apply appropriate CORS, rate limiting, and error handling that does not leak internals.
4. THE system SHALL resolve AWS credentials via the standard AWS credential chain / roles, never hard-coded.

---

## Requirement 17 — Kiro University Lesson Evidence

**User Story:** As a challenge reviewer, I want the repository to demonstrate all seven Kiro
University lessons, so that the project qualifies.

### Acceptance Criteria
1. THE repository SHALL retain `.kiro/specs/` demonstrating spec-driven development (Lesson 1).
2. THE repository SHALL retain `.kiro/steering/` documents that influence implementation (Lesson 2).
3. THE repository SHALL retain executable `.kiro/hooks/` (Lesson 3).
4. THE repository SHALL contain property-based tests traceable to requirements (Lesson 4).
5. THE repository SHALL contain at least one relevant Kiro Power and a custom `namma-ooru-power` (Lesson 5).
6. THE repository SHALL contain MCP configuration and documented evidence of MCP use (Lesson 6).
7. THE repository SHALL demonstrate the seventh lesson (Custom Agents) with a real custom agent definition and documented evidence (Lesson 7).
8. THE README SHALL contain a lesson-to-evidence mapping table.
