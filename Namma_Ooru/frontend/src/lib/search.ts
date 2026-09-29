/**
 * Pure, deterministic helpers that shape a `SearchResult` into the labelled chips
 * the search UI renders. Keeping this free of React and I/O keeps the search
 * components presentational (Coding steering: data shaping lives outside
 * components) and makes the derivation unit-testable.
 */

import type { DestinationFilters, SearchIntent } from '../api/types';
import { CATEGORY_LABELS } from './catalog';
import type { DestinationCategory } from '../api/types';

/** A labelled active-filter chip derived from the deterministic `SearchFilters`. */
export type ActiveFilterChip = {
  /** Stable key for React and tests. */
  key: string;
  /** The filter dimension, e.g. "City" or "Category". */
  label: string;
  /** The human-readable filter value, e.g. "Madurai" or "Temples". */
  value: string;
};

function categoryLabel(category: string): string {
  return CATEGORY_LABELS[category as DestinationCategory] ?? category;
}

/**
 * Derive the visible active-filter chips from the deterministic filters the
 * search mapped to. Only set constraints produce a chip, so an unconstrained
 * search yields no chips. `tags` are AND-intersected on the backend, so each tag
 * is shown as its own chip.
 */
export function activeFilterChips(filters: DestinationFilters): ActiveFilterChip[] {
  const chips: ActiveFilterChip[] = [];
  if (filters.city) {
    chips.push({ key: 'city', label: 'City', value: filters.city });
  }
  if (filters.district) {
    chips.push({ key: 'district', label: 'District', value: filters.district });
  }
  if (filters.category) {
    chips.push({ key: 'category', label: 'Category', value: categoryLabel(filters.category) });
  }
  for (const tag of filters.tags ?? []) {
    chips.push({ key: `tag:${tag}`, label: 'Tag', value: tag });
  }
  if (filters.family_friendly === true) {
    chips.push({ key: 'family_friendly', label: 'Suited to', value: 'Families' });
  }
  if (filters.hidden_gems === true) {
    chips.push({ key: 'hidden_gems', label: 'Focus', value: 'Hidden gems' });
  }
  return chips;
}

/** A labelled chip describing one facet of the AI-derived search intent. */
export type IntentChip = {
  key: string;
  label: string;
  value: string;
};

/**
 * Derive labelled chips describing the AI's interpretation of the query. Only
 * recognized facets produce a chip. This is AI-derived interpretation and must be
 * badged separately from source catalog data (AI/RAG steering).
 */
export function intentChips(intent: SearchIntent): IntentChip[] {
  const chips: IntentChip[] = [];
  if (intent.location) {
    chips.push({ key: 'location', label: 'Location', value: intent.location });
  }
  if (typeof intent.duration_days === 'number') {
    chips.push({
      key: 'duration',
      label: 'Duration',
      value: `${intent.duration_days} ${intent.duration_days === 1 ? 'day' : 'days'}`,
    });
  }
  if (intent.category) {
    chips.push({ key: 'category', label: 'Category', value: categoryLabel(intent.category) });
  }
  for (const interest of intent.interests) {
    chips.push({ key: `interest:${interest}`, label: 'Interest', value: interest });
  }
  if (intent.travel_style) {
    chips.push({ key: 'travel_style', label: 'Style', value: intent.travel_style });
  }
  if (intent.budget) {
    chips.push({ key: 'budget', label: 'Budget', value: intent.budget });
  }
  if (intent.group_context) {
    chips.push({ key: 'group_context', label: 'Group', value: intent.group_context });
  }
  return chips;
}
