# Implementation Plan: Namma Ooru

## Overview
This plan implements Namma Ooru in incremental, testable slices. It starts with shared frontend,
backend, data, and CDK foundations; then builds catalog discovery, deterministic travel services,
and AI integrations. Each property-based test is a separate optional subtask immediately after the
implementation it validates, following Kiro’s correctness workflow. The optional marker `*` means
that a property test may be deferred for an MVP, but it remains in the plan and dependency graph as
challenge evidence. No property test invokes Bedrock or AWS services.

## Tasks
- [ ] 1. Establish project foundations
  - [ ] 1.1 Create the React TypeScript Vite frontend structure with Tailwind, React Query, routing, and accessible shared loading, empty, and error components.
    - _Requirements: 1.1, 1.3, 1.4, 2.3, 11.4_
  - [ ] 1.2 Create the Python 3.11 FastAPI backend structure with Pydantic request models, dependency injection, structured exception mapping, and LocalMockAIProvider.
    - _Requirements: 4.1, 5.3, 11.1, 11.3_
  - [ ] 1.3 Add frontend and backend formatter, linter, type-check, unit-test, and property-test configuration.
    - _Requirements: 13.3, 13.6_
  - [ ] 1.4 Add `.env.example` and `.gitignore` rules that document non-secret configuration without committing credentials.
    - _Requirements: 11.2_

- [ ] 2. Implement the source-attributed destination catalog
  - [ ] 2.1 Create the Destination JSON Schema, Tamil Nadu district/category vocabularies, source-attribution model, and data validator.
    - _Requirements: 3.2, 3.3, 3.4, 3.5, 3.6_
  - [ ] 2.2 Create the JSON DestinationRepository and a DynamoDB-compatible repository interface with city grouping and deterministic filter support.
    - _Requirements: 1.2, 2.1, 3.1_
  - [ ] 2.3 Create `GET /api/destinations`, `GET /api/destinations/{id}`, and `GET /api/cities/{city}` endpoints with not-found handling.
    - _Requirements: 1.5, 2.1, 2.2, 2.4, 11.3_
  - [ ]* 2.4 Write a property-based test for filter intersection soundness.
    - **Property 1: Filter intersection soundness**
    - **Validates: Requirements 4.4**
  - [ ]* 2.5 Write a property-based test for filter removal preservation.
    - **Property 2: Filter removal preservation**
    - **Validates: Requirements 4.5**
  - [ ]* 2.6 Write a property-based test for filter monotonicity.
    - **Property 3: Filter monotonicity**
    - **Validates: Requirements 4.4**

- [ ] 3. Build discovery, city, and destination experiences
  - [ ] 3.1 Implement the home page hero, catalog sections, cards, search entry, and skeleton/empty states using the catalog API.
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_
  - [ ] 3.2 Implement city and destination pages with nullable-field rendering, source links, nearby navigation, and responsive layouts.
    - _Requirements: 2.1, 2.2, 2.3, 2.4_
  - [ ] 3.3 Implement the MapProvider interface, MapLibre provider, filtered marker endpoint, marker preview, and detail navigation.
    - _Requirements: 9.1, 9.2, 9.3, 9.4_
  - [ ]* 3.4 Write a property-based test for map marker filter soundness.
    - **Property 12: Map marker filter soundness**
    - **Validates: Requirements 9.1, 9.2**

- [ ] 4. Implement natural-language search and recommendations
  - [ ] 4.1 Implement SearchIntent, SearchFilters, deterministic FilterService, and `POST /api/search` with keyword/tag fallback.
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_
  - [ ] 4.2 Implement search controls and structured search-result rendering with active filters and fallback status.
    - _Requirements: 4.2, 4.3_
  - [ ] 4.3 Implement RecommendationService, interest and themed-journey endpoints, and Surprise Me selection.
    - _Requirements: 8.1, 8.2, 8.3, 8.4_
  - [ ] 4.4 Implement the personalized discovery, themed journey, and Beyond the Tourist Map UI sections.
    - _Requirements: 8.1, 8.2, 8.3_
  - [ ]* 4.5 Write a property-based test for recommendation catalog membership.
    - **Property 11: Recommendation catalog membership**
    - **Validates: Requirements 8.1, 8.2, 8.3, 8.4**

- [ ] 5. Implement the deterministic itinerary domain
  - [ ] 5.1 Create Itinerary, ItineraryDay, ItineraryActivity, constraint, and structured-operation models.
    - _Requirements: 6.1, 6.2, 6.3, 7.1_
  - [ ] 5.2 Implement ItineraryService generation with catalog validation, destination uniqueness, time ordering, duration validation, and coordinate-aware ordering.
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_
  - [ ] 5.3 Implement ItineraryService operations for add, remove, replace, reorder, and constraints with unchanged-itinerary failure behavior.
    - _Requirements: 7.2, 7.3, 7.4_
  - [ ]* 5.4 Write a property-based test for itinerary day-count preservation.
    - **Property 4: Itinerary day-count preservation**
    - **Validates: Requirements 6.1**
  - [ ]* 5.5 Write a property-based test for itinerary catalog-reference validity.
    - **Property 5: Itinerary catalog-reference validity**
    - **Validates: Requirements 6.2**
  - [ ]* 5.6 Write a property-based test for itinerary temporal validity.
    - **Property 6: Itinerary temporal validity**
    - **Validates: Requirements 6.2, 6.3**
  - [ ]* 5.7 Write a property-based test for itinerary uniqueness when repeats are disabled.
    - **Property 7: Itinerary uniqueness when repeats are disabled**
    - **Validates: Requirements 6.5**
  - [ ]* 5.8 Write a property-based test for edit invariant preservation.
    - **Property 8: Edit invariant preservation**
    - **Validates: Requirements 7.3**
  - [ ]* 5.9 Write a property-based test for remove operation locality.
    - **Property 9: Remove operation locality**
    - **Validates: Requirements 7.2**
  - [ ]* 5.10 Write a property-based test for replace operation validity.
    - **Property 10: Replace operation validity**
    - **Validates: Requirements 7.1, 7.2**

- [ ] 6. Deliver itinerary planning and conversational editing
  - [ ] 6.1 Implement AIProvider itinerary-candidate selection and structured edit parsing with schema validation and LocalMockAIProvider responses.
    - _Requirements: 6.4, 7.1, 11.1_
  - [ ] 6.2 Implement itinerary generation and itinerary-edit API endpoints that route all structural changes through ItineraryService.
    - _Requirements: 6.1, 6.2, 6.3, 6.5, 7.2, 7.3, 7.4_
  - [ ] 6.3 Implement the itinerary planner, day timeline, generated-content label, and conversational edit interface.
    - _Requirements: 6.6, 7.1, 7.4_

- [ ] 7. Implement reviews and rating aggregates
  - [ ] 7.1 Create Review models, an in-memory review repository for development, and a persistence interface for the production adapter.
    - _Requirements: 10.1, 10.2_
  - [ ] 7.2 Implement ReviewService validation, review creation, aggregate calculation, and `GET/POST /api/destinations/{id}/reviews` endpoints.
    - _Requirements: 10.1, 10.2, 10.3_
  - [ ] 7.3 Implement ReviewPanel, review submission, rating distribution, recent-review rendering, and accessible error states.
    - _Requirements: 10.1, 10.2, 10.3, 11.4_
  - [ ]* 7.4 Write a property-based test for review acceptance boundaries.
    - **Property 13: Review acceptance boundary**
    - **Validates: Requirements 10.1**
  - [ ]* 7.5 Write a property-based test for review rejection boundaries.
    - **Property 14: Review rejection boundary**
    - **Validates: Requirements 10.2**
  - [ ]* 7.6 Write a property-based test for review aggregate consistency.
    - **Property 15: Review aggregate consistency**
    - **Validates: Requirements 10.3**

- [ ] 8. Integrate Bedrock Knowledge Base and grounded AI
  - [ ] 8.1 Implement the data-to-Knowledge-Base document builder, including S3 sidecar metadata documents and source URLs.
    - _Requirements: 3.2, 5.1_
  - [ ] 8.2 Create CDK data and AI constructs for S3 source data, S3 Vectors, Bedrock Knowledge Base, Bedrock data source, and least-privilege roles.
    - _Requirements: 5.1, 12.1, 12.4_
  - [ ] 8.3 Implement BedrockAIProvider retrieval, generated-text/source separation, unavailable-information behavior, and bounded dependency failures.
    - _Requirements: 5.2, 5.3, 5.4, 11.3_
  - [ ] 8.4 Implement ChatWidget, source links, AI labels, AI review summaries, and AI itinerary narrative enrichment.
    - _Requirements: 5.5, 10.4, 10.5, 6.6_

- [ ] 9. Provision deployable backend and frontend infrastructure
  - [ ] 9.1 Create CDK BackendStack with Lambda, HTTP API, safe CORS origins, API URL output, and scoped runtime permissions.
    - _Requirements: 11.2, 11.5, 12.1, 12.2, 12.3, 12.4_
  - [ ] 9.2 Create CDK FrontendStack and MonitoringStack with Amplify Hosting configuration, backend URL injection, logs, alarms, and dashboard resources.
    - _Requirements: 12.1, 12.5_
  - [ ] 9.3 Write CDK assertions and synthesis tests for stack resources, outputs, CORS, and IAM scopes.
    - _Requirements: 11.2, 11.5, 12.1, 12.3, 12.4, 12.5_

- [ ] 10. Complete Kiro University evidence and quality automation
  - [ ] 10.1 Implement and verify source-format, backend-test, data-validation, and pre-completion hooks against the scaffolded commands.
    - _Requirements: 13.3_
  - [ ] 10.2 Activate and use the Namma Ooru Power skills for destination curation, itinerary planning, content, and review analysis; record evidence.
    - _Requirements: 13.4_
  - [ ] 10.3 Use the destination-curator and spec-reviewer Custom Agents for dataset and specification review; record evidence.
    - _Requirements: 13.5_
  - [ ] 10.4 Configure the approved MCP servers through Kiro settings and retain an evidence record of AWS and repository research.
    - _Requirements: 13.5_
  - [ ] 10.5 Add property-test tags and traceability evidence for every implemented design property.
    - _Requirements: 13.6_

- [ ] 11. Checkpoint - Validate the catalog and discovery slice
  - Run frontend and backend unit tests, linting, type checks, and the dataset validator; resolve failures before AI integration.

- [ ] 12. Checkpoint - Validate the itinerary and review slice
  - Run itinerary and review unit tests plus all selected optional property tests; resolve failures before production AI integration.

- [ ] 13. Final checkpoint - Ensure all required tests and validation commands pass
  - Run unit tests, all selected property tests, CDK assertions, `cdk synth`, data validation, linting, type checks, and secret scanning.

## Notes
- Tasks marked with `*` are optional and can be skipped for a faster MVP; they remain required
  evidence for the completed Lesson 4 implementation.
- Each optional property-test subtask maps one design property to the exact acceptance criteria it
  validates. Property tests are close to their deterministic implementation to catch defects early.
- Property tests use at least 100 Hypothesis examples and mocks/in-memory repositories only.
- Dataset schema validation, UI layout, AWS CDK, AWS service behavior, and deployment smoke tests
  use schema, unit, integration, visual, CDK assertion, or smoke tests—not PBT.
- Checkpoint tasks are parent tasks and are intentionally omitted from the dependency graph.

## Task Dependency Graph
```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2", "1.3", "1.4"] },
    { "id": 1, "tasks": ["2.1", "2.2", "8.2"] },
    { "id": 2, "tasks": ["2.3", "2.4", "2.5", "2.6", "3.1", "8.1"] },
    { "id": 3, "tasks": ["3.2", "3.3", "4.1"] },
    { "id": 4, "tasks": ["3.4", "4.2", "4.3", "5.1"] },
    { "id": 5, "tasks": ["4.4", "4.5", "5.2", "7.1"] },
    { "id": 6, "tasks": ["5.3", "6.1", "7.2", "8.3", "9.1"] },
    { "id": 7, "tasks": ["5.4", "5.5", "5.6", "5.7", "5.8", "5.9", "5.10", "6.2", "7.3", "8.4", "9.2", "10.1"] },
    { "id": 8, "tasks": ["6.3", "7.4", "7.5", "7.6", "9.3", "10.2", "10.3", "10.4"] },
    { "id": 9, "tasks": ["10.5"] }
  ]
}
```