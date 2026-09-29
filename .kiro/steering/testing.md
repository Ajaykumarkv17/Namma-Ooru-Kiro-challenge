# Testing Steering — Namma Ooru

## Layers
- **Property-based tests (Hypothesis)** validate only universal deterministic-domain rules (the
  itinerary, filters, recommendations, map-marker filtering, and review services). The canonical
  properties are in `.kiro/specs/namma-ooru/design.md` under `## Correctness Properties`; each
  property maps to one optional task in `tasks.md`. Dataset schema validation, UI, CDK, AWS
  behavior, and I/O use the appropriate non-PBT test types.
- **Example-based unit tests** cover specific edge cases and API contracts.
- **Integration tests** exercise FastAPI endpoints (TestClient) and CDK stacks
  (`aws-cdk.assertions`) under `infra/tests/`.

## Rules
- New feature or bug fix ⇒ add/adjust tests. Bug fixes get a regression test.
- Keep AI-dependent code testable by injecting a mock AI provider; do not require live AWS in CI.
- Property tests must trace to a design property id (Properties 1–15) and the requirement clause it validates.
- The backend test hook (Lesson 3) runs unit + property tests on backend changes; the
  pre-completion hook verifies tests pass, no secrets are committed, and docs are updated.

## Commands (indicative)
- Backend: `pytest`, `pytest backend/tests/property`.
- Data: `python data/scripts/validate.py`.
- Frontend: `npm test`, `tsc --noEmit`, `eslint`.
- Infra: `pytest infra/tests`, `cdk synth`.
