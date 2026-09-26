# Namma Ooru — Discover the Tamil Nadu you haven't seen

Namma Ooru is an AI-powered Tamil Nadu travel discovery and trip-planning platform built for the
**Kiro University Challenge 2026**, with **Kiro as the primary development tool**. It helps users
discover destinations across Tamil Nadu, search in natural language, chat with a grounded AI guide,
generate and conversationally edit multi-day itineraries, and read/write reviews — through a
premium, culturally-grounded UI.

> This repository currently contains the **planning artifacts** (Kiro spec, steering, hooks,
> powers, custom agents, MCP evidence, property-test plan). Application code is implemented in
> phases per `.kiro/specs/namma-ooru/tasks.md`.

## Problem statement
Tamil Nadu's travel content is fragmented across many sources and skewed toward a handful of
famous cities. Trip planning is manual and time-consuming, and AI answers often hallucinate facts.
Namma Ooru builds a broad, source-attributed destination dataset and a Retrieval-Augmented AI
layer so discovery is wide and answers stay grounded in real data.

## Features
- Beautiful discovery home (hero, search, popular destinations/cities, categories, hidden gems,
  recommendations, interactive map).
- Rich city and destination pages with grounded facts and graceful "Information unavailable".
- AI natural-language search returning structured results.
- Amazon Bedrock RAG chatbot grounded in a Namma Ooru Knowledge Base.
- AI multi-day itinerary planner (hero feature) with conversational editing.
- Personalized discovery, "Surprise Me", themed journeys, "Beyond the Tourist Map".
- Reviews & ratings with AI review summaries clearly labelled as AI-generated.

## Architecture
```
React + TS + Vite (Amplify Hosting)
      │ REST/JSON
FastAPI (Lambda + API Gateway via Mangum)
   ├── Destination repository (JSON now → DynamoDB-ready)
   ├── Deterministic cores: itinerary, filters, review rules  ← property-tested
   └── AI layer (Bedrock) behind an interface (+ local mock)
             │
   Bedrock Knowledge Base ── S3 (source docs) + S3 Vectors (vector store)  → RetrieveAndGenerate
```
Full detail: [`.kiro/specs/namma-ooru/design.md`](.kiro/specs/namma-ooru/design.md).

## Technology stack
- **Frontend:** React, TypeScript, Vite, Tailwind CSS, React Query, Framer Motion, MapLibre GL.
- **Backend:** Python 3.11, FastAPI, Pydantic, Mangum; pytest + Hypothesis.
- **AI:** Amazon Bedrock (LLM + Titan embeddings), Bedrock Knowledge Bases.
- **Data/RAG:** S3 (KB source), S3 Vectors (vector store); JSON dataset → DynamoDB-ready.
- **IaC:** AWS CDK v2 (Python) under `infra/`.

## AI architecture
The chatbot and review summaries answer **only** from retrieved knowledge. Retrieved context and
generated text are kept in separate fields end-to-end so grounding is auditable; if the Knowledge
Base lacks relevant content, the assistant says so rather than inventing facts. See
[`.kiro/steering/ai-rag.md`](.kiro/steering/ai-rag.md).

## Bedrock Knowledge Base architecture / S3 & S3 Vectors role
The validated destination dataset is converted into RAG-ready chunks (`data/kb/`) carrying
retrieval metadata (district, city, category, subcategory, region, heritage, UNESCO, travel type),
uploaded to an **S3** source bucket. A **Bedrock Knowledge Base** ingests them into **S3 Vectors**,
and `RetrieveAndGenerate` powers grounded answers. (This pattern was verified via the AWS docs MCP —
see [`.kiro/evidence/mcp.md`](.kiro/evidence/mcp.md).)

## Data model
Canonical destination schema (with source attribution and nullable-when-unknown fields) is defined
in `design.md` §3 and enforced by `data/schema/destination.schema.json` + `data/scripts/validate.py`.

## Local setup
```bash
# Backend
cd backend && python -m venv .venv && . .venv/Scripts/activate   # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend
cd frontend && npm install && npm run dev
```
> These commands become available as the phases in `tasks.md` are implemented.

## AWS setup
1. Configure AWS credentials via the standard chain (profile / SSO / role) — never hard-coded.
2. Deploy infra: `cd infra && pip install -r requirements.txt && cdk deploy --all`.
3. Deploy order (Req 15.5): `data_stack` + `ai_stack` + `backend_stack` first, run the frontend
   locally against the backend API URL output, then deploy `frontend_stack` (Amplify).

## Environment variables
See `.env.example` (no secrets committed). Typical keys: `AWS_REGION`, `BEDROCK_MODEL_ID`,
`BEDROCK_KB_ID`, `KB_S3_BUCKET`, `API_BASE_URL`, `GITHUB_PERSONAL_ACCESS_TOKEN` (for MCP, env only).

## Running the application
Run backend locally (or against the deployed API), then the frontend dev server; open the printed
local URL.

## Testing
- Property-based (primary): `pytest backend/tests/property` (properties P1–P26).
- Unit/integration: `pytest backend/tests`, `pytest infra/tests`, `cdk synth`.
- Data validation: `python data/scripts/validate.py`.
- Frontend: `npm test`, `tsc --noEmit`, `eslint`.

## Kiro University Implementation

| Lesson | Implementation | Evidence |
| --- | --- | --- |
| Lesson 1 | Spec-Driven Development | [`.kiro/specs/`](.kiro/specs/namma-ooru/) |
| Lesson 2 | Steering | [`.kiro/steering/`](.kiro/steering/) |
| Lesson 3 | Hooks | [`.kiro/hooks/`](.kiro/hooks/) |
| Lesson 4 | Property-Based Testing | [`property-tests.md`](.kiro/specs/namma-ooru/property-tests.md) |
| Lesson 5 | Powers | [`namma-ooru-power/`](namma-ooru-power/) |
| Lesson 6 | MCP | [`.kiro/evidence/mcp.md`](.kiro/evidence/mcp.md) |
| Lesson 7 | Custom Agents | [`.kiro/agents/`](.kiro/agents/) |

Full evidence index: [`.kiro/evidence/kiro-university.md`](.kiro/evidence/kiro-university.md).
Bonus-lesson evaluation is scheduled in `tasks.md` Phase 14.4 and documented in the evidence file
if implemented.

## Repository note
The Git repository and history are preserved. No commits are created automatically — commit and
push when you choose to.

## License
MIT.
