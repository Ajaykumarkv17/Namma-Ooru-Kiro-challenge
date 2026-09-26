# Skill: Destination Curation

Curate Tamil Nadu destinations into the Namma Ooru schema with reliable, source-attributed data.

## When to use
Discovering, extracting, normalizing, or validating a TN destination record.

## Rules
1. **Source priority:** TN Tourism/TTDC → TN district portals → HR&CE (temples) / Archaeology
   (monuments) → Incredible India → other reputable sources. Cross-reference; never trust one page.
2. **Never invent** hours, fees, coordinates, history, temple info, distances, contact, or
   accessibility. Unknown ⇒ `null`.
3. **Schema:** populate all fields in `data/schema/destination.schema.json`. Slug id = `<city>-<name>`.
4. **Attribution:** every record keeps `source_urls` + `sources[]` (name, type, retrieved date,
   notes). Flag conflicts for human review; prefer the authoritative government source.
5. **Coverage:** favour breadth across districts and diverse categories, including hidden gems.
6. **Coordinates:** must fall within the TN bounding box (lat 8.0–13.6, lon 76.2–80.4) or be null.

## Output
A schema-valid JSON destination record (or batch) plus a list of any fields left null and why, and
any conflicts flagged for review.
