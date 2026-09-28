# Namma Ooru — Technical Design

This design implements the requirements in `requirements.md`. It favours a clean, realistically
completable architecture over unnecessary complexity (no microservices, Kubernetes, Kafka,
Redis, complex auth, or over-engineered infra). Local/mock data is used early while keeping the
architecture ready for the real Amazon Bedrock + S3 + S3 Vectors integration.

---

## 1. Architecture Overview

```
                         ┌─────────────────────────────────────────────┐
                         │                Users (Web)                   │
                         └───────────────────────┬─────────────────────┘
                                                 │ HTTPS
                         ┌───────────────────────▼─────────────────────┐
                         │  Frontend — React + TypeScript + Vite        │
                         │  (Tailwind, Framer Motion, MapLibre)         │
                         │  Hosted on AWS Amplify Hosting               │
                         └───────────────────────┬─────────────────────┘
                                                 │ REST/JSON
                         ┌───────────────────────▼─────────────────────┐
                         │  Backend — FastAPI (Python 3.11)             │
                         │  API: search, chat, itinerary, reviews,      │
                         │  destinations, recommendations               │
                         │  Deployed via API Gateway + Lambda (Mangum)  │
                         └──────┬───────────────────────┬───────────────┘
                                │                       │
             ┌──────────────────▼──────┐     ┌──────────▼───────────────────────┐
             │ Destination Data Store  │     │ AI / RAG Layer                    │
             │ (JSON dataset → later    │     │ Amazon Bedrock (LLM + embeddings) │
             │ DynamoDB) + reviews      │     │ Bedrock Knowledge Base            │
             └─────────────────────────┘     │  ├── S3 (KB source documents)     │
                                             │  └── S3 Vectors (vector store)    │
                                             └───────────────────────────────────┘
```

### Key decisions
- **Frontend:** React + TypeScript + Vite; Tailwind CSS for styling; Framer Motion for
  transitions; MapLibre GL (open, replaceable) behind a `MapProvider` abstraction (Req 10.4).
- **Backend:** FastAPI. Runs locally for early development and deploys to AWS Lambda behind API
  Gateway using Mangum. This satisfies "test with deployed backend + local frontend, then deploy
  frontend to Amplify" (Req 15.5).
- **Data:** Start with a versioned JSON dataset (`data/destinations/*.json`) validated by a
  Python validator. The repository model abstracts storage so it can move to DynamoDB without
  changing feature logic (Req 3.4).
- **AI:** Amazon Bedrock foundation model for generation + Titan embeddings; a Bedrock Knowledge
  Base with S3 as the document source and S3 Vectors as the vector store for RAG (Req 5).
- **IaC:** AWS CDK v2 (Python) under `infra/` with separate stacks (Req 15).

---

## 2. Repository Structure

```
.
├── .kiro/
│   ├── specs/namma-ooru/{requirements.md,design.md,tasks.md,property-tests.md}
│   ├── steering/*.md
│   ├── hooks/*.json
│   ├── agents/*.json                 # Lesson 7 — Custom Agents
│   ├── settings/mcp.json             # Lesson 6 — MCP
│   ├── evidence/kiro-university.md   # Lesson mapping + evidence
│   └── ugmdu.json
├── namma-ooru-power/                 # Lesson 5 — custom Power
│   ├── plugin.json
│   └── skills/{destination-curation,itinerary-planning,tamil-nadu-travel-content,review-analysis}/
├── frontend/                         # React + TS + Vite app
├── backend/                          # FastAPI app + tests (incl. property-based)
├── data/                             # researched dataset + schema + validator
│   ├── schema/destination.schema.json
│   ├── destinations/*.json
│   ├── kb/                           # RAG-ready documents/chunks for S3
│   └── scripts/{validate.py,build_kb.py}
├── infra/                            # AWS CDK v2 (Python)
│   ├── app.py, cdk.json, requirements.txt
│   ├── stacks/{frontend_stack,backend_stack,data_stack,ai_stack,monitoring_stack}.py
│   ├── constructs/
│   └── tests/
├── docs/                             # data research docs, architecture diagrams
└── README.md
```

---

## 3. Data Model (Req 3, 13)

Canonical destination schema (JSON Schema in `data/schema/destination.schema.json`). Uncertain
fields are nullable; nothing is invented (Req 13.4).

```jsonc
{
  "id": "madurai-meenakshi-amman-temple",       // slug, unique
  "name": "Meenakshi Amman Temple",
  "alternate_names": ["Meenakshi Sundareswarar Temple"],
  "city": "Madurai",
  "district": "Madurai",
  "region": "South Tamil Nadu",
  "category": "Temples",                          // enum
  "subcategory": "Dravidian temple",
  "description": "Short summary.",
  "detailed_description": "Longer description.",
  "historical_significance": null,               // null when not verified
  "cultural_significance": null,
  "latitude": 9.9195,
  "longitude": 78.1193,
  "address": "Madurai Main, Madurai, Tamil Nadu",
  "best_time_to_visit": "Oct–Mar",
  "recommended_duration": "2–3 hours",
  "opening_hours": null,                          // dynamic → verify at source
  "entry_fee": null,
  "official_website": null,
  "source_urls": ["https://www.tamilnadutourism.tn.gov.in/..."],
  "sources": [{"name":"TN Tourism","type":"government","retrieved":"2026-09-27","notes":null}],
  "image_reference": "madurai/meenakshi-1.jpg",
  "tags": ["temple","heritage","architecture"],
  "nearby_places": ["madurai-thirumalai-nayakkar-mahal"],
  "is_hidden_gem": false,
  "is_heritage": true,
  "is_unesco": false,
  "family_friendly": true,
  "nature_related": false,
  "adventure_related": false,
  "average_rating": 4.7,
  "review_count": 128,
  "popularity": {"score": 95, "rank_in_city": 1}
}
```

### Category enum
`Temples, Heritage, Beaches, Hills, Waterfalls, Nature, Wildlife, Food, Culture, Adventure,
Photography, Hidden Gems` (extensible — Req 3.2). Subcategories are free-form but validated
against a controlled vocabulary list where possible.

### District list
Validated against the official 38 Tamil Nadu districts (stored in `data/schema/districts.json`).

### Reviews model
```jsonc
{ "id": "uuid", "destination_id": "slug", "rating": 5, "text": "…",
  "tags": ["architecture"], "created_at": "ISO-8601", "author": "display name" }
```
Invariant: `rating ∈ {1,2,3,4,5}` and `destination_id` must exist (Req 11.2, 11.3).

---

## 4. Backend API Design (Req 4–8, 11)

FastAPI with Pydantic models. All endpoints validate input (Req 16.2).

| Method | Path | Purpose | Requirements |
|---|---|---|---|
| GET | `/api/destinations` | list/filter destinations | 1, 3, 4 |
| GET | `/api/destinations/{id}` | destination detail | 2, 3 |
| GET | `/api/cities/{city}` | grouped city page data | 2 |
| POST | `/api/search` | NL search → structured results | 4 |
| POST | `/api/chat` | RAG chatbot turn | 5 |
| POST | `/api/itinerary` | generate itinerary | 6 |
| POST | `/api/itinerary/edit` | conversational edit | 7 |
| POST | `/api/recommendations` | interest-based + Surprise Me | 8, 9 |
| GET | `/api/destinations/{id}/reviews` | list reviews + stats + AI summary | 11 |
| POST | `/api/destinations/{id}/reviews` | submit review | 11 |
| GET | `/api/map` | map markers (filterable) | 10 |

### Search intent extraction (Req 4)
`/api/search` sends the query to Bedrock with a strict JSON schema prompt to extract
`{location, duration, category, interests, travel_style, budget, group_context}`, then filters
the catalog. Filtering is pure/deterministic so property tests (Req 4.3, 4.4) can verify filter
invariants without invoking the model. If the model is unavailable, fall back to keyword/tag
matching (Req 4.5).

### Itinerary engine (Req 6, 7)
Two-stage design so correctness is testable:
1. **Deterministic core** (`itinerary/core.py`): given candidate destinations + constraints,
   produces a valid day-by-day plan. Pure functions with invariants: exactly N days, no illegal
   duplicates, valid references, positive durations, ordered non-overlapping times, proximity
   ordering (nearest-neighbour over coordinates). This is the target of property-based tests.
2. **AI layer** (`itinerary/ai.py`): uses Bedrock to select candidates, write "why visit"
   narratives and food suggestions, and interpret conversational edits into structured
   operations (`remove`, `add`, `replace`, `reorder`, `constrain`) that are then applied by the
   deterministic core so invariants always hold after edits (Req 7.3).

---

## 5. AI / RAG Architecture (Req 5, 11.5)

```
Question ──► /api/chat ──► Retrieve (Bedrock KB: RetrieveAndGenerate)
                              │  query embedding (Titan) → S3 Vectors search
                              │  → top-k chunks from S3 KB docs
                              ▼
                         Grounded context (kept separate from generation)
                              │
                              ▼
                         Bedrock LLM generates answer citing retrieved sources
```

- **Knowledge source:** `data/kb/*.md|json` chunks built from the validated dataset by
  `data/scripts/build_kb.py`, uploaded to an S3 bucket. Each chunk carries metadata (district,
  city, category, subcategory, region, heritage, unesco, travel_type) for retrieval filtering
  (Req 5, data section).
- **Vector store:** S3 Vectors, populated via the Bedrock Knowledge Base ingestion job.
- **Grounding & anti-hallucination:** The system prompt instructs the model to answer only from
  retrieved context and to say when information is unavailable (Req 5.3). Retrieved context and
  generated text are represented as separate fields in the API response.
- **Review summaries (Req 11.5):** A separate Bedrock summarization call over a destination's
  reviews, returning `{positives[], concerns[]}`, labelled as AI-generated (Req 11.6).

---

## 6. AWS Architecture & CDK Stacks (Req 15, 16)

| Stack | Resources | Notes |
|---|---|---|
| `data_stack` | S3 (KB source bucket), DynamoDB (destinations, reviews) optional, S3 Vectors bucket | least-privilege access |
| `ai_stack` | Bedrock Knowledge Base, S3 Vectors index, IAM roles for KB ingestion & retrieval | model access via Bedrock |
| `backend_stack` | Lambda (FastAPI via Mangum), API Gateway (HTTP API), IAM exec role, CORS | scoped Bedrock + data permissions |
| `frontend_stack` | Amplify Hosting app (or S3+CloudFront fallback) | connects to backend API URL output |
| `monitoring_stack` | CloudWatch dashboards, log groups, alarms | observability |

Principles: reusable constructs, environment-specific config via CDK context, no hardcoded
credentials, CloudFormation outputs (API URL, bucket names, KB id) for wiring frontend/backend.
Credentials resolve through the standard AWS chain / IAM roles (Req 16.4).

**Deployment path (Req 15.5):** deploy `data_stack` + `ai_stack` + `backend_stack` first; run the
frontend locally against the deployed backend URL; once verified, deploy `frontend_stack`
(Amplify).

---

## 7. Frontend Design (Req 1, 2, 9, 10, 12)

- **Routing:** Home, City/`:city`, Destination/`:id`, Search, Itinerary, Map, Discover.
- **State/data:** React Query for API calls with built-in loading/error states; skeletons for
  loading; explicit empty and error components (Req 12.3).
- **Design system:** Tailwind theme with a Tamil Nadu-inspired palette (temple gold, kaavi/ochre,
  deep maroon, coastal teal) and modern typography; reusable `DestinationCard`, `SectionHeader`,
  `RatingStars`, `ChatWidget`, `ItineraryTimeline`, `JourneyPicker`, `MapView` components.
- **Accessibility:** semantic landmarks, focus management, keyboard-navigable widgets, alt text,
  contrast-checked palette (Req 12.4).
- **Map abstraction:** `MapProvider` interface with a `MapLibreProvider` default; swappable for a
  production provider (Req 10.4).

---

## 8. Testing Strategy (Req 4, 6, 7, 11, 14; Lesson 4)

- **Property-based tests (Hypothesis, Python)** target the deterministic cores. Following Kiro's
  correctness workflow, properties are extracted from the EARS requirements (inline
  *Correctness / Properties* blocks in `requirements.md`) and run as **optional** subtasks placed
  **after** each feature's core implementation subtasks in `tasks.md` (2.5, 4.4, 6.4, 7.4, 8.5).
  `property-tests.md` is the consolidated traceability index. Examples: itinerary invariants,
  review rating bounds, filter soundness, dataset validity.
- **Example-based unit tests** for API contracts and edge cases.
- **Integration tests** for API endpoints (FastAPI TestClient) and CDK assertions
  (`aws-cdk.assertions`) in `infra/tests/`.
- **Data validation** (`data/scripts/validate.py`) enforces Req 14 and runs as a hook.

---

## 9. Kiro University Lesson Mapping (design-level)

| Lesson | Where it lives in this design |
|---|---|
| 1 Specs | `.kiro/specs/namma-ooru/` (this spec) drives all phases |
| 2 Steering | `.kiro/steering/` conventions applied to frontend/backend/AI/data |
| 3 Hooks | `.kiro/hooks/` run lint/format/type-check, backend tests, data validation, pre-completion checks |
| 4 Property-Based Testing | deterministic cores (§4, §8) + `property-tests.md` |
| 5 Powers | relevant installed Power + `namma-ooru-power/` custom Power |
| 6 MCP | `.kiro/settings/mcp.json` (AWS docs, GitHub) used for research/validation |
| 7 Custom Agents | `.kiro/agents/` — destination-curation & spec-review agents |

Bonus lessons are evaluated in `tasks.md` Phase 14 after the seven required lessons.

---

## 10. Risks & Mitigations
- **Bedrock/S3 Vectors availability & cost** → build behind an interface with a local mock so the
  app is demoable without live AWS; gate live calls behind env config.
- **Data accuracy** → strict validator, source attribution, null-over-invention, human-review
  flags for conflicts.
- **Scope** → phased delivery; deterministic cores first so AI can be layered on tested logic.
- **Map provider lock-in** → `MapProvider` abstraction.
