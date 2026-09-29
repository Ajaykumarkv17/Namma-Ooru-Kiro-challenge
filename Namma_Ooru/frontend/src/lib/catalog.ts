/**
 * Pure, deterministic helpers that derive the home-page catalog sections from the
 * `Destination[]` returned by `GET /api/destinations`. Keeping this logic free of
 * React and I/O makes it unit-testable and keeps components presentational
 * (Coding steering: data shaping lives outside components).
 */

import type { Destination, DestinationCategory } from '../api/types';

/** The 12 accepted categories with display labels, for the categories section. */
export const CATEGORY_LABELS: Record<DestinationCategory, string> = {
  temples: 'Temples',
  heritage: 'Heritage',
  beaches: 'Beaches',
  hills: 'Hills',
  waterfalls: 'Waterfalls',
  nature: 'Nature',
  wildlife: 'Wildlife',
  food: 'Food',
  culture: 'Culture',
  adventure: 'Adventure',
  photography: 'Photography',
  'hidden-gems': 'Hidden Gems',
};

/** A city grouping for the "popular cities" section. */
export type CitySummary = {
  city: string;
  district: string;
  destinationCount: number;
  topScore: number;
};

/** A category grouping for the "categories" section. */
export type CategorySummary = {
  category: DestinationCategory;
  label: string;
  destinationCount: number;
};

function byPopularityDesc(a: Destination, b: Destination): number {
  const scoreDelta = b.popularity.popularity_score - a.popularity.popularity_score;
  if (scoreDelta !== 0) {
    return scoreDelta;
  }
  // Stable, deterministic tie-break by name so ordering never depends on input order.
  return a.name.localeCompare(b.name);
}

/** Most popular destinations, ranked by popularity score then name. */
export function selectPopularDestinations(
  destinations: readonly Destination[],
  limit = 8,
): Destination[] {
  return [...destinations].sort(byPopularityDesc).slice(0, limit);
}

/** Hidden gems: destinations flagged as hidden or in the Hidden Gems category. */
export function selectHiddenGems(destinations: readonly Destination[], limit = 8): Destination[] {
  return [...destinations]
    .filter((d) => d.is_hidden_gem || d.category === 'hidden-gems')
    .sort(byPopularityDesc)
    .slice(0, limit);
}

/**
 * Recommended destinations: highly rated places, ranked by average rating then
 * rating count. Destinations without a rating are excluded so the section only
 * surfaces places with real visitor signal (Trust-through-grounding).
 */
export function selectRecommendedDestinations(
  destinations: readonly Destination[],
  limit = 8,
): Destination[] {
  return [...destinations]
    .filter((d) => d.popularity.rating_average !== null)
    .sort((a, b) => {
      const ratingDelta = (b.popularity.rating_average ?? 0) - (a.popularity.rating_average ?? 0);
      if (ratingDelta !== 0) {
        return ratingDelta;
      }
      const countDelta = b.popularity.rating_count - a.popularity.rating_count;
      if (countDelta !== 0) {
        return countDelta;
      }
      return a.name.localeCompare(b.name);
    })
    .slice(0, limit);
}

/** Popular cities, ranked by number of destinations then by their top score. */
export function selectPopularCities(
  destinations: readonly Destination[],
  limit = 6,
): CitySummary[] {
  const byCity = new Map<string, CitySummary>();
  for (const destination of destinations) {
    const existing = byCity.get(destination.city);
    if (existing) {
      existing.destinationCount += 1;
      existing.topScore = Math.max(existing.topScore, destination.popularity.popularity_score);
    } else {
      byCity.set(destination.city, {
        city: destination.city,
        district: destination.district,
        destinationCount: 1,
        topScore: destination.popularity.popularity_score,
      });
    }
  }
  return [...byCity.values()]
    .sort((a, b) => {
      const countDelta = b.destinationCount - a.destinationCount;
      if (countDelta !== 0) {
        return countDelta;
      }
      const scoreDelta = b.topScore - a.topScore;
      if (scoreDelta !== 0) {
        return scoreDelta;
      }
      return a.city.localeCompare(b.city);
    })
    .slice(0, limit);
}

/** Categories that have at least one matching destination, in vocabulary order. */
export function selectCategories(destinations: readonly Destination[]): CategorySummary[] {
  const counts = new Map<DestinationCategory, number>();
  for (const destination of destinations) {
    counts.set(destination.category, (counts.get(destination.category) ?? 0) + 1);
  }
  return (Object.keys(CATEGORY_LABELS) as DestinationCategory[])
    .filter((category) => counts.has(category))
    .map((category) => ({
      category,
      label: CATEGORY_LABELS[category],
      destinationCount: counts.get(category) ?? 0,
    }));
}

/** URL-safe slug for a city, used for `/cities/:citySlug` navigation. */
export function citySlug(city: string): string {
  return city
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
}

/**
 * Reconstruct a searchable city name from a `/cities/:citySlug` route param.
 * Hyphens become spaces so a slug such as `the-nilgiris` matches the catalogued
 * city "The Nilgiris"; the backend matches case-insensitively, so exact casing
 * does not need to be restored.
 */
export function deSlugCity(slug: string): string {
  return slug.trim().replace(/-+/g, ' ').trim();
}
