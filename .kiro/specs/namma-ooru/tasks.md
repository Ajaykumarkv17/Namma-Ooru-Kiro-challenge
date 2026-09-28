# Namma Ooru — Implementation Tasks

Phased plan implementing `design.md` against `requirements.md`. Each task lists the requirements
it satisfies. Do not start large-scale implementation until the spec is approved.

## Conventions
- `[ ]` not started.
- **Property-based tests follow the official Kiro workflow:** properties are extracted from the
  EARS requirements (see the *Correctness / Properties* block under each requirement in
  `requirements.md`) and are surfaced in the design phase. In the task list, each feature's
  **core implementation subtasks come first**, and a **property-based test subtask appears after
  them, marked `(optional PBT)`** — because Kiro treats PBTs as optional by default so you can
  focus on core implementation first, then run them to validate behavior.
- `property-tests.md` is a **traceability index** (requirement ↔ property ↔ task), not a separate
  phase of work.

---

## Phase 1 — Project foundation & architecture
- [ ] 1.1 Scaffold `frontend/` (React + TS + Vite + Tailwind + React Query + Framer Motion). _(Req 12)_
- [ ] 1.2 Scaffold `backend/` (FastAPI, Pydantic, uvicorn, pytest, hypothesis, Mangum). _(Req 4–8,11,16)_
- [ ] 1.3 Add repo config: lint/format/type-check (ruff+black+mypy, eslint+prettier+tsc), pre-commit. _(Req 12, Lesson 3)_
- [ ] 1.4 Create `.env.example` (no secrets) and `.gitignore` entries for `.env`. _(Req 16.1)_
- [ ] 1.5 Wire steering conventions into scaffold. _(Lesson 2)_

## Phase 2 — Destination data model & explorer
- [ ] 2.1 Author `data/schema/destination.schema.json` + `districts.json` + category enum. _(Req 3)_
- [ ] 2.2 Implement destination repository abstraction (JSON now, DynamoDB-ready). _(Req 3.4)_
- [ ] 2.3 Implement `GET /api/destinations`, `/{id}`, `/api/cities/{city}`. _(Req 1,2,3)_
- [ ] 2.4 Implement `data/scripts/validate.py` (all Req 14 checks; non-zero exit on failure). _(Req 14)_
- [ ] 2.5 _(optional PBT)_ Dataset & validation properties **P15–P21** after data exists. _(Req 3.1,3.2,3.5,3.6,14.1)_

### Phase 2b — Data acquisition & research (Req 13)
- [ ] 2b.1 Document source strategy in `docs/data-research.md` (TN Tourism/TTDC, district portals, HR&CE, Archaeology, Incredible India). _(Req 13.1)_
- [ ] 2b.2 Collect destinations across most TN districts and diverse categories with source attribution. _(Req 13.2, 3.6)_
- [ ] 2b.3 Normalize → deduplicate → cross-source validate → schema validate → flag conflicts for review. _(Req 13.3, 13.5)_
- [ ] 2b.4 Keep dynamic fields null when unverified; link to official sources. _(Req 13.4, 13.6)_
- [ ] 2b.5 Use the `namma-ooru-power` destination-curation & tamil-nadu-travel-content skills and the destination-curator custom agent during collection. _(Lessons 5,7)_

## Phase 3 — Rich UI & destination pages
- [ ] 3.1 Home page: hero, search bar, CTA, popular destinations/cities, categories, hidden gems, recommended, map entry. _(Req 1)_
- [ ] 3.2 City page with grouped sections + fallbacks. _(Req 2)_
- [ ] 3.3 Destination detail page. _(Req 2,3)_
- [ ] 3.4 Loading/empty/error/skeleton states + accessibility pass. _(Req 12)_

## Phase 4 — Search & filtering
- [ ] 4.1 Deterministic filter engine (pure) + `/api/destinations` filters. _(Req 4.3,4.4)_
- [ ] 4.2 `POST /api/search` with Bedrock intent extraction + structured results + keyword fallback. _(Req 4)_
- [ ] 4.3 Search UI with filters and result cards. _(Req 4,12)_
- [ ] 4.4 _(optional PBT)_ Filter/search & map-filter properties **P22–P26** after 4.1–4.3. _(Req 4.3,4.4,8.3,10.2)_

## Phase 5 — Amazon Bedrock chatbot & Knowledge Base
- [ ] 5.1 `data/scripts/build_kb.py` → RAG-ready chunks with retrieval metadata into `data/kb/`. _(Req 5,13)_
- [ ] 5.2 CDK `data_stack` + `ai_stack`: S3 KB bucket, S3 Vectors, Bedrock KB, IAM. _(Req 15)_
- [ ] 5.3 `POST /api/chat` RetrieveAndGenerate with grounding + separated context/answer + local mock. _(Req 5)_
- [ ] 5.4 `ChatWidget` embedded across app. _(Req 5.4)_

## Phase 6 — AI itinerary planner (hero feature)
- [ ] 6.1 Deterministic itinerary core with invariants (exactly N days, no illegal dupes, valid refs, positive/ordered times, proximity ordering). _(Req 6.2,6.5,6.6,6.7)_
- [ ] 6.2 AI candidate selection + narratives + food suggestions. _(Req 6.1,6.3,6.4)_
- [ ] 6.3 `POST /api/itinerary` + `ItineraryTimeline` UI. _(Req 6,12)_
- [ ] 6.4 _(optional PBT)_ Itinerary generation properties **P1–P6** after 6.1–6.3. _(Req 6.2,6.5,6.6,6.7)_

## Phase 7 — Conversational itinerary editing
- [ ] 7.1 Edit-intent parser → structured ops (add/remove/replace/reorder/constrain). _(Req 7.1)_
- [ ] 7.2 Apply ops via deterministic core preserving invariants + unaffected parts. _(Req 7.2,7.3)_
- [ ] 7.3 `POST /api/itinerary/edit` + conversational UI; explain unsatisfiable edits. _(Req 7.4)_
- [ ] 7.4 _(optional PBT)_ Itinerary edit properties **P7–P9** after 7.1–7.3. _(Req 7.1,7.2,7.3)_

## Phase 8 — Reviews & ratings
- [ ] 8.1 Review model + storage; reject ratings outside 1–5; require valid destination. _(Req 11.1,11.2,11.3)_
- [ ] 8.2 Stats: average, distribution, count, recent. _(Req 11.4)_
- [ ] 8.3 AI review summary (positives/concerns) labelled AI-generated. _(Req 11.5,11.6)_
- [ ] 8.4 Review UI (submit + display). _(Req 11,12)_
- [ ] 8.5 _(optional PBT)_ Review properties **P10–P14** after 8.1–8.4. _(Req 11.1,11.2,11.3,11.4)_

## Phase 9 — Personalization & creative discovery
- [ ] 9.1 Interest selection → recommendations. _(Req 8.1,8.3)_
- [ ] 9.2 "Surprise Me". _(Req 8.2)_
- [ ] 9.3 Journey picker + "Beyond the Tourist Map". _(Req 9)_
- [ ] 9.4 Interactive map view with filters, markers, previews behind `MapProvider`. _(Req 10)_
  _(map-filter property P25 and recommendation property P26 are covered by the optional PBT task 4.4)_

## Phase 10 — Kiro Hooks (Lesson 3)
- [ ] 10.1 Lint/format/type-check hook on source changes. _(Req 17.3)_
- [ ] 10.2 Backend test hook on backend changes (runs unit + any implemented PBTs). _(Req 17.3)_
- [ ] 10.3 Data validation hook on dataset changes. _(Req 14.3)_
- [ ] 10.4 Pre-completion checks hook (tests pass, no secrets, docs updated). _(Req 16,17)_

## Phase 11 — Powers (Lesson 5)
- [ ] 11.1 Finalize `namma-ooru-power/` (plugin.json + 4 skills). _(Req 17.5)_
- [ ] 11.2 Use a relevant installed Power (e.g. aws-drawio for architecture diagram, strands for agent) and document contribution. _(Req 17.5)_

## Phase 12 — MCP integration (Lesson 6)
- [ ] 12.1 Configure `.kiro/settings/mcp.json` (AWS docs, GitHub). _(Req 17.6)_
- [ ] 12.2 Use MCP for AWS/Bedrock research + repo review; document evidence. _(Req 17.6)_

## Phase 13 — Testing, security, accessibility, performance + bonus
- [ ] 13.1 Consolidate/confirm all optional PBTs (P1–P26) have been run and are green. _(Req 17.4)_
- [ ] 13.2 Integration tests (API + CDK assertions). _(Req 15)_
- [ ] 13.3 Security pass: input validation, CORS, rate limiting, secret scanning. _(Req 16)_
- [ ] 13.4 Accessibility & performance audit. _(Req 12)_
- [ ] 13.5 Evaluate the two official Bonus Lessons; implement if natural without risking the seven. _(Extra credit)_

## Phase 14 — Demo polish & documentation
- [ ] 14.1 README (overview, architecture, AI/KB, data model, setup, AWS setup, env vars, run, testing, lesson mapping). _(Req 18)_
- [ ] 14.2 `docs/data-research.md` (sources, discovery, dedup, conflict resolution, validation, KB prep, refresh). _(Req 13 docs)_
- [ ] 14.3 `.kiro/evidence/kiro-university.md` lesson-to-evidence mapping. _(Req 17.8)_
- [ ] 14.4 Demo script covering the 9 demo-first steps. _(Req 17 demo-first)_

## Custom Agents (Lesson 7) — used throughout
- [ ] X.1 `.kiro/agents/destination-curator.json` used in Phase 2b. _(Req 17.7)_
- [ ] X.2 `.kiro/agents/spec-reviewer.json` used to review spec/PRs. _(Req 17.7)_

---

## Requirement → Task coverage matrix
| Req | Core tasks | Optional PBT task |
|---|---|---|
| 1 | 2.3, 3.1 | — |
| 2 | 2.3, 3.2, 3.3 | — |
| 3 | 2.1, 2.2, 2.3, 3.3 | 2.5 (P15–P21) |
| 4 | 4.1, 4.2, 4.3 | 4.4 (P22–P24) |
| 5 | 5.1–5.4 | — |
| 6 | 6.1–6.3 | 6.4 (P1–P6) |
| 7 | 7.1–7.3 | 7.4 (P7–P9) |
| 8 | 9.1, 9.2 | 4.4 (P26) |
| 9 | 9.3 | — |
| 10 | 9.4 | 4.4 (P25) |
| 11 | 8.1–8.4 | 8.5 (P10–P14) |
| 12 | 1.1, 3.1–3.4, 4.3, 13.4 | — |
| 13 | 2b.1–2b.5, 5.1, 14.2 | — |
| 14 | 2.4, 10.3, 8.5/2.5 | — |
| 15 | 5.2, 13.2 | — |
| 16 | 1.4, 10.4, 13.3 | — |
| 17 | Phases 10–12, 13.1, 14.3, X.1–X.2 | 13.1 |
