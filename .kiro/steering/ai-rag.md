# AI / RAG Steering — Namma Ooru

## Grounding & anti-hallucination
- The chatbot and review summaries answer **only from retrieved knowledge**. If the Knowledge Base
  lacks relevant content, say so — never invent facts, hours, fees, coordinates, history, or
  distances.
- Keep **retrieved context** and **generated text** in separate fields end-to-end (retrieval →
  API response → UI), so grounding is auditable.
- Where possible, cite the source destination(s) behind an answer.

## Prompt design
- Use explicit system prompts that state the grounding rule and the "say I don't know" fallback.
- For structured outputs (search intent, itinerary, edit ops, review summaries) require strict
  JSON matching a documented schema; validate the JSON before use and reject/repair on mismatch.
- Keep prompts versioned in the backend so changes are reviewable.

## Structured AI outputs
- **Search intent:** `{location, duration, category, interests, travel_style, budget, group}`.
- **Itinerary:** candidate destination ids + per-activity narrative; structural assembly is done
  by the deterministic core, not free-text from the model.
- **Edit ops:** `{op: add|remove|replace|reorder|constrain, target, args}` applied by the core.
- **Review summary:** `{positives: string[], concerns: string[]}`, labelled AI-generated.

## Models & safety
- Bedrock foundation model for generation; Titan for embeddings. Selection via env config.
- Never place secrets in prompts. Sanitize user input before templating into prompts.
- Provide a local mock implementation so all AI features are demoable/testable without live AWS.
