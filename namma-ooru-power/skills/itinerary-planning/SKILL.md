# Skill: Itinerary Planning

Produce logically ordered, constraint-aware multi-day Tamil Nadu itineraries.

## When to use
Generating or editing a multi-day trip plan.

## Rules
1. An N-day request yields exactly N days; days numbered 1..N.
2. Order activities to minimize travel (proximity via coordinates / nearby_places).
3. Respect opening hours where known, recommended durations, user interests, travel style, and
   budget. Do not fabricate hours or durations — if unknown, use conservative, clearly-estimated
   values and say they are estimates.
4. No destination repeats within an itinerary unless explicitly allowed.
5. Each activity: time/order, place (valid catalog id), approx duration (>0), why-visit, travel
   context, nearby food/break suggestion.
6. Structural assembly is deterministic; only narrative prose is generative.
7. Conversational edits map to structured ops (add/remove/replace/reorder/constrain) and preserve
   the rest of the plan; if an edit is impossible, explain why and change nothing.

## Output
A day-by-day plan referencing only valid destinations, honoring all invariants above.
