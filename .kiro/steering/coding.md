# Coding Steering — Namma Ooru

## React / TypeScript
- Function components + hooks. `strict` TypeScript; no `any` unless justified with a comment.
- Data fetching through React Query; never fetch in components without cache/loading/error states.
- Components are presentational where possible; data shaping lives in hooks/services.
- Named exports for components; PascalCase component files; colocate component + styles + test.
- No destination data hard-coded in components — always via API/service layer.

## Python / FastAPI
- Python 3.11; type hints everywhere; Pydantic models for all request/response bodies.
- Keep **pure deterministic cores** (itinerary, filters, review rules) free of I/O and AWS calls
  so they are unit- and property-testable.
- Services encapsulate I/O (data store, Bedrock). Routers stay thin.
- Format with `black`, lint with `ruff`, type-check with `mypy`.

## Naming
- Destination ids are slugs: `<city>-<name>` lowercased, hyphenated, unique.
- API paths are plural nouns (`/api/destinations`); verbs only for actions (`/api/itinerary/edit`).
- Env vars are UPPER_SNAKE_CASE and documented in `.env.example`.

## Error handling
- Backend returns structured errors `{error, detail}` with correct HTTP status; never leak stack
  traces or internals to clients.
- Frontend surfaces user-friendly error states; log technical detail to the console/monitoring.
- Fail closed on validation; fail soft on optional AI enrichment (fall back gracefully).

## API design
- Validate and sanitize all input at the boundary (Pydantic + explicit checks).
- Deterministic, documented response shapes; keep AI-generated text in clearly named fields
  separate from retrieved/source data.
