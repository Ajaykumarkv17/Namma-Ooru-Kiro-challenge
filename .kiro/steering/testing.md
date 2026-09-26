# Testing Steering — Namma Ooru

## Layers
- **Property-based tests (Hypothesis)** are the primary correctness mechanism for the deterministic
  cores (itinerary engine, filter engine, review rules, dataset invariants). See
  `.kiro/specs/namma-ooru/property-tests.md` for the requirement→property map.
- **Example-based unit tests** cover specific edge cases and API contracts.
- **Integration tests** exercise FastAPI endpoints (TestClient) and CDK stacks
  (`aws-cdk.assertions`) under `infra/tests/`.

## Rules
- New feature or bug fix ⇒ add/adjust tests. Bug fixes get a regression test.
- Keep AI-dependent code testable by injecting a mock AI provider; do not require live AWS in CI.
- Property tests must trace to a requirement id and a property id (P1..P26).
- The backend test hook (Lesson 3) runs unit + property tests on backend changes; the
  pre-completion hook verifies tests pass, no secrets are committed, and docs are updated.

## Commands (indicative)
- Backend: `pytest`, `pytest backend/tests/property`.
- Data: `python data/scripts/validate.py`.
- Frontend: `npm test`, `tsc --noEmit`, `eslint`.
- Infra: `pytest infra/tests`, `cdk synth`.
