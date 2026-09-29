/**
 * Pure, deterministic helpers for the personalized-discovery UI. They shape the
 * eight themed journeys and the interest options into display metadata and format
 * a Surprise Me pick's suggested duration. Keeping this free of React and I/O
 * keeps the discovery components presentational (Coding steering: data shaping
 * lives outside components) and makes the derivation unit-testable.
 */

import type { ThemedJourney } from '../api/types';

/** A themed journey with its display name and short description (Requirement 8.3). */
export type JourneyOption = {
  slug: ThemedJourney;
  label: string;
  description: string;
};

/**
 * The eight themed journeys in display order, with the exact display names from
 * the requirement. `slug` is the wire value sent to `POST /api/recommendations`.
 */
export const JOURNEY_OPTIONS: readonly JourneyOption[] = [
  {
    slug: 'spiritual-journey',
    label: 'Spiritual Journey',
    description: 'Temples and sacred sites across Tamil Nadu.',
  },
  {
    slug: 'hill-escape',
    label: 'Hill Escape',
    description: 'Cool hill stations, gardens, and viewpoints.',
  },
  {
    slug: 'coastal-escape',
    label: 'Coastal Escape',
    description: 'Beaches and seaside towns along the coast.',
  },
  {
    slug: 'food-trail',
    label: 'Food Trail',
    description: 'Regional cuisine and street-food experiences.',
  },
  {
    slug: 'heritage-journey',
    label: 'Heritage Journey',
    description: 'Forts, palaces, and monuments steeped in history.',
  },
  {
    slug: 'nature-escape',
    label: 'Nature Escape',
    description: 'Waterfalls, forests, and wildlife retreats.',
  },
  {
    slug: 'photography-trip',
    label: 'Photography Trip',
    description: 'Scenic spots framed for the perfect shot.',
  },
  {
    slug: 'hidden-gems',
    label: 'Hidden Gems',
    description: 'Lesser-known places beyond the tourist map.',
  },
];

/** Look up a journey's display label from its slug, falling back to the slug. */
export function journeyLabel(slug: ThemedJourney): string {
  return JOURNEY_OPTIONS.find((option) => option.slug === slug)?.label ?? slug;
}

/** A selectable interest for the personalized-discovery picker (Requirement 8.1). */
export type InterestOption = {
  /** The value sent to `POST /api/recommendations` as an interest string. */
  value: string;
  label: string;
};

/**
 * Curated interest options for the interests picker. Each value matches a catalog
 * category or a common tag so the deterministic backend can match by category or
 * tag (Requirement 8.1). The category slugs mirror `DestinationCategory`.
 */
export const INTEREST_OPTIONS: readonly InterestOption[] = [
  { value: 'temples', label: 'Temples' },
  { value: 'heritage', label: 'Heritage' },
  { value: 'beaches', label: 'Beaches' },
  { value: 'hills', label: 'Hills' },
  { value: 'waterfalls', label: 'Waterfalls' },
  { value: 'nature', label: 'Nature' },
  { value: 'wildlife', label: 'Wildlife' },
  { value: 'food', label: 'Food' },
  { value: 'culture', label: 'Culture' },
  { value: 'adventure', label: 'Adventure' },
  { value: 'photography', label: 'Photography' },
  { value: 'hidden-gems', label: 'Hidden gems' },
];

/**
 * Toggle an interest within a selection, returning a new array (never mutating).
 * A present interest is removed; an absent one is appended, preserving order.
 */
export function toggleInterest(selected: readonly string[], interest: string): string[] {
  return selected.includes(interest)
    ? selected.filter((value) => value !== interest)
    : [...selected, interest];
}

/**
 * Format a suggested duration in minutes as a human-readable string, or return
 * `null` when the source record has no verified duration so the UI can show
 * "Information unavailable" rather than a fabricated value (Data steering).
 */
export function formatSuggestedDuration(minutes: number | null): string | null {
  if (minutes === null || minutes <= 0) {
    return null;
  }
  const hours = Math.floor(minutes / 60);
  const remainder = minutes % 60;
  const parts: string[] = [];
  if (hours > 0) {
    parts.push(`${hours} ${hours === 1 ? 'hour' : 'hours'}`);
  }
  if (remainder > 0) {
    parts.push(`${remainder} ${remainder === 1 ? 'minute' : 'minutes'}`);
  }
  return parts.join(' ');
}
