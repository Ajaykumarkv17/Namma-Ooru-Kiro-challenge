# Data Steering — Namma Ooru

## Source priority (research)
1. Official Tamil Nadu Tourism / TTDC.
2. Government of Tamil Nadu district portals.
3. TN government departments: HR&CE (temples), Department of Archaeology (monuments/heritage).
4. Government of India tourism (Incredible India).
5. Other reputable tourism/reference sources only when necessary.

Never treat a single "Tamil Nadu places" page as the complete dataset. Cross-reference sources.

## Coverage goals
- Span most of the 38 TN districts, not only famous cities.
- Include diverse categories: temples, heritage, UNESCO, forts, palaces, museums, beaches, hills,
  waterfalls, lakes, dams, wildlife, forests, bird sanctuaries, wetlands, caves, archaeological
  sites, churches, mosques, Jain heritage, cultural, food, adventure, photography, hidden gems,
  viewpoints, islands/coastal, family attractions.

## Quality rules
- **Never invent** hours, fees, coordinates, history, temple info, distances, contact, or
  accessibility. Unknown ⇒ `null` and the UI shows "Information unavailable".
- Every factual record keeps source attribution: `source_urls`, source name, type, retrieval date,
  and notes for conflicts.
- On conflicting sources, flag for review and prefer the authoritative government source.
- Distinguish stable vs dynamic info (hours, fees, closures, access, weather, festivals); link to
  official sources for verification of dynamic info.

## Pipeline (repeatable)
research → collection → extraction → normalization → deduplication → cross-source validation →
schema validation → human-review flags → dataset → S3 KB docs → Bedrock/S3 Vectors → AI features.

## Validation (enforced by hook)
Required fields, valid districts, valid categories, valid coordinate ranges, duplicate places,
duplicate aliases, invalid ratings, invalid relationships, missing sources, malformed URLs,
incorrect district/category mappings, empty descriptions. Failure ⇒ non-zero exit.

## KB preparation
Build clean RAG chunks with retrieval metadata: district, city, category, subcategory, region,
heritage status, UNESCO status, travel type. The chatbot answers from these chunks, not the
foundation model's internal knowledge.
