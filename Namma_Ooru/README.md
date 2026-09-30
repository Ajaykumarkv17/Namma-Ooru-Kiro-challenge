# Namma Ooru

Namma Ooru is a Tamil Nadu travel discovery and planning application. It combines a source-attributed destination catalog with deterministic itinerary scheduling and optional AI-assisted candidate selection and conversational edits.

## Local development

Run the backend test suite from the backend directory so the `app` package is importable:

```powershell
Set-Location backend
python -m pytest tests -q
```

Start the API locally with the configured FastAPI development command, then start the Vite frontend from `frontend/`. Set `VITE_API_BASE_URL` when the frontend should target a separately deployed backend. Copy the repository `.env.example` only for local configuration; AWS authentication uses the standard credential chain and credentials must not be committed.

## Itinerary planner

The **Plan your Tamil Nadu journey** page creates an AI-assisted itinerary from a trip focus and a day count (1–14). The displayed timeline is labelled **AI itinerary** and shows each visit’s start time, approximate duration, rationale, travel context, and break suggestion.

AI output is limited to selecting catalog candidates and translating an edit request. The backend validates those candidates, and `ItineraryService` alone performs destination validation, scheduling, duration assignment, repeat handling, and every structural edit. This preserves catalog-only destinations, positive visit durations, and non-overlapping activities.

### API contracts

- `POST /api/itineraries` accepts an `ItineraryRequest` with `destination_context`, `day_count`, optional `constraints`, and `allow_repeats`; it returns a scheduled `Itinerary`.
- `POST /api/itineraries/{id}/edits` accepts `{ "request": "..." }`; it returns either a changed itinerary plus its parsed operation or an unchanged itinerary with an explanation when no valid edit is possible.

The local demo stores generated itineraries in memory. Restarting the backend clears these temporary plans.
