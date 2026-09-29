# Kiro University Challenge 2026 — Lesson Evidence (Namma Ooru)

This document maps each of the seven required Kiro University lessons to concrete, retained
artifacts in this repository, plus the bonus-lesson evaluation.

The seven lessons: **Spec-Driven Development, Steering, Hooks, Property-Based Testing, Powers,
MCP, and Custom Agents.** Kiro is the primary development tool: specs, steering, hooks, powers,
MCP, custom agents, and property-based tests are all first-class artifacts under `.kiro/` and
`namma-ooru-power/`.

## Lesson mapping

| Lesson | Implementation | Evidence (paths) |
|---|---|---|
| 1 — Spec-Driven Development | Full feature spec drives every phase | `.kiro/specs/namma-ooru/requirements.md`, `design.md`, `tasks.md` |
| 2 — Steering | 8 steering docs shaping product/arch/code/UI/AI/security/testing/data | `.kiro/steering/*.md` |
| 3 — Hooks | 4 executable hooks (lint/format/type-check, backend tests, data validation, pre-completion checks) | `.kiro/hooks/format-lint-typecheck.json`, `backend-tests.json`, `validate-destination-data.json`, `pre-completion-checks.json` |
| 4 — Property-Based Testing | Fifteen universal properties in the canonical design section; one optional PBT subtask per property after its deterministic implementation | `.kiro/specs/namma-ooru/design.md` (`## Correctness Properties`, Properties 1–15), `tasks.md` (2.4–2.6, 3.4, 4.5, 5.4–5.10, 7.4–7.6), (impl) `backend/tests/property/` |
| 5 — Powers | Relevant installed Power + custom `namma-ooru-power` with 4 skills | `namma-ooru-power/plugin.json`, `namma-ooru-power/skills/*`; usage below |
| 6 — MCP | AWS docs + GitHub MCP; real call validated the Bedrock/S3 Vectors RAG design | `.kiro/evidence/mcp.md` |
| 7 — Custom Agents | Two custom agents used in development (curation + spec review) | `.kiro/agents/destination-curator.json`, `.kiro/agents/spec-reviewer.json` |

## Lesson 7 identification (the seventh lesson)
The brief explicitly enumerated Lessons 1–6 (Specs, Steering, Hooks, Property-Based Testing,
Powers, MCP) and directed me to identify the seventh from the official lesson set rather than
invent one. Kiro's seven core building blocks are Specs, Steering, Hooks, Property-Based Testing
(Correctness), Powers, MCP, and **Custom Agents** (agents you define with scoped tools/permissions,
invocable as sub-agents). The seventh lesson is therefore **Custom Agents**, demonstrated by:
- `destination-curator` — a write-scoped agent (data/docs only) enforcing the data-quality and
  source-attribution rules during Phase 2b data acquisition.
- `spec-reviewer` — a read-only agent that reviews spec/PR changes against requirements, steering,
  and the seven-lesson mapping.

Evidence of use will be recorded here as each agent is invoked during implementation.

## Lesson 5 — how the Power contributes
- `namma-ooru-power` skills (`destination-curation`, `itinerary-planning`,
  `tamil-nadu-travel-content`, `review-analysis`) encode the domain rules so Kiro produces
  grounded, source-attributed outputs. Activated on keywords: Tamil Nadu, destination, itinerary,
  travel, temple, trip, tourism.
- A relevant installed Power will also be used and documented (e.g. `aws-drawio` to author the
  architecture diagram in `docs/`, and/or `strands` if an agent runtime is prototyped).

## Lesson 6 — MCP usage summary
See `.kiro/evidence/mcp.md`. A real `aws-docs` MCP query confirmed that Bedrock Knowledge Bases
support **S3 Vectors** as a fully-managed vector store with **RetrieveAndGenerate**, validating
`design.md` §5–§6 (Requirement 5) before implementation.

## Bonus lessons (extra credit)
Evaluated in `tasks.md` Phase 14.4, only after the seven required lessons are solid. Candidate
bonus opportunities that fit naturally:
- **Autonomous / sub-agent orchestration** using the custom agents above for parallel data
  curation.
- **AWS-native agent runtime** (Bedrock AgentCore / Strands power) for the chatbot, if it does not
  jeopardize the required seven.

Bonus work, if implemented, will get its own evidence section here.
