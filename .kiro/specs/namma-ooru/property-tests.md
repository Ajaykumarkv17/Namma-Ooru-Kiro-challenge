# Namma Ooru — Property-Based Testing Traceability Index (Lesson 4)

This is the **consolidated traceability index** for property-based testing. It is not a separate
phase of work. The properties themselves are extracted from the EARS acceptance criteria and live
**inline** in `requirements.md` under each requirement's *Correctness / Properties* block, exactly
as Kiro's correctness workflow surfaces them (requirement → executable property → linked task).

How this follows the official Kiro workflow:
- **Properties come from requirements** (design phase surfaces them, linked to requirement + task).
- **PBTs run during task execution and are optional by default** — each feature's core
  implementation subtasks are done first, then an `(optional PBT)` subtask runs the properties.
  See the per-phase optional PBT subtasks in `tasks.md` (2.5, 4.4, 6.4, 7.4, 8.5) and the
  consolidation step 13.1.

Tooling: **Hypothesis** (Python) in `backend/tests/property/`. Properties target the
**deterministic cores** (itinerary engine, filter engine, validators, review rules) so most can
be checked without invoking Bedrock.

## Property → task map
| Properties | Requirement | Optional PBT task |
|---|---|---|
| P1–P6 | Req 6 (itinerary) | 6.4 |
| P7–P9 | Req 7 (itinerary edit) | 7.4 |
| P10–P14 | Req 11 (reviews) | 8.5 |
| P15–P21 | Req 3 / 14 (dataset) | 2.5 |
| P22–P24 | Req 4 (search/filter) | 4.4 |
| P25 | Req 10 (map filter) | 4.4 |
| P26 | Req 8 (recommendations) | 4.4 |

---

## 1. Itinerary properties (Req 6, 7)

| ID | Property | Requirement |
|---|---|---|
| P1 | For any N in a reasonable range, a generated itinerary has exactly N days. | 6.2 |
| P2 | No destination appears twice within one itinerary (unless explicitly allowed by input flag). | 6.6 |
| P3 | Every activity references an id present in the destination catalog. | 6.5 |
| P4 | Every activity duration is strictly positive. | 6.7 |
| P5 | Within a day, activity start times are strictly increasing and do not overlap given durations. | 6.7 |
| P6 | Day ordering is 1..N with no gaps or repeats. | 6.2, 6.7 |
| P7 | After any single edit op (add/remove/replace/reorder/constrain), all invariants P2–P6 still hold. | 7.3 |
| P8 | A `remove` edit does not change any activity other than removing the target. | 7.2 |
| P9 | A `replace` edit changes exactly one activity and the replacement is a valid, distinct destination. | 7.1, 7.2 |

**Strategies:** random destination catalogs (valid coordinates, durations), random constraints
(days 1–7, budget tiers, interests), random edit-op sequences.

---

## 2. Review properties (Req 11)

| ID | Property | Requirement |
|---|---|---|
| P10 | A persisted review always has an integer rating in [1,5]. | 11.1 |
| P11 | Any rating outside [1,5] (incl. non-integers, negatives) is rejected and never persisted. | 11.2 |
| P12 | Every stored review references a destination id that exists in the catalog. | 11.3 |
| P13 | Reported average rating equals the mean of stored ratings (within float tolerance). | 11.4 |
| P14 | Rating distribution counts sum to the review count. | 11.4 |

---

## 3. Destination data properties (Req 3, 13, 14)

| ID | Property | Requirement |
|---|---|---|
| P15 | Every destination's district is in the official TN district list. | 3.5, 14.1 |
| P16 | Every destination's category is in the allowed category enum. | 3.2, 14.1 |
| P17 | Every destination has all required non-nullable fields present. | 3.1, 14.1 |
| P18 | latitude ∈ [8.0, 13.6] and longitude ∈ [76.2, 80.4] (TN bounding box) or is null. | 14.1 |
| P19 | No two destinations share the same id; alias sets do not collide across records. | 14.1 |
| P20 | Every factual record has at least one source reference. | 3.6, 14.1 |
| P21 | Description fields are non-empty (not whitespace) when present. | 14.1 |

---

## 4. Search & filter properties (Req 4, 10)

| ID | Property | Requirement |
|---|---|---|
| P22 | For any set of active filters, every result satisfies every active filter (soundness). | 4.3 |
| P23 | Removing one filter never introduces a result that violates another still-active filter. | 4.4 |
| P24 | Filtering is monotonic: adding a filter never grows the result set. | 4.3 |
| P25 | Map markers under a category/city filter only include matching destinations. | 10.2 |
| P26 | Every recommendation / Surprise Me result exists in the catalog. | 8.3 |

---

## Notes
- Properties P1–P9, P22–P26 run against pure functions and require no AWS.
- P10–P14 run against the review service with an in-memory store.
- P15–P21 run against the researched dataset and overlap with `data/scripts/validate.py`, giving
  two independent checks of the same invariants.
- Property tests are wired into the backend test hook (Phase 10.2) and the pre-completion hook
  (Phase 10.4).
