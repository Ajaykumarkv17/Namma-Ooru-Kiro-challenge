# Skill: Review Analysis

Summarize destination reviews into balanced, clearly-labelled AI summaries.

## When to use
Generating an AI review summary for a destination with enough reviews.

## Rules
1. Only summarize from the provided reviews; do not add outside claims.
2. Produce structured output `{positives: string[], concerns: string[]}` — e.g. positives like
   architecture, cultural experience, photography; concerns like crowding, parking, waiting time.
3. Reflect genuine frequency/themes; do not exaggerate or invent sentiment.
4. Label output clearly as AI-generated and distinct from individual user reviews.
5. Never include personally identifying details from reviews in the summary.

## Output
A short positives/concerns summary plus the count of reviews it was derived from.
