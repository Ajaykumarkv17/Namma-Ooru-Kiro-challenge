import { describe, expect, it } from 'vitest';

import type { Destination } from '../api/types';
import {
  citySlug,
  deSlugCity,
  selectCategories,
  selectHiddenGems,
  selectPopularCities,
  selectPopularDestinations,
  selectRecommendedDestinations,
} from './catalog';

function makeDestination(overrides: Partial<Destination> = {}): Destination {
  return {
    id: 'test-place',
    name: 'Test Place',
    alternate_names: [],
    city: 'Madurai',
    district: 'madurai',
    region: 'South Tamil Nadu',
    category: 'temples',
    subcategory: null,
    description: 'A catalogued place.',
    detailed_description: null,
    historical_significance: null,
    cultural_significance: null,
    latitude: null,
    longitude: null,
    address: null,
    best_time_to_visit: null,
    recommended_duration_minutes: null,
    opening_hours: null,
    entry_fee: null,
    official_website: null,
    source_urls: [],
    sources: [],
    image_reference: null,
    tags: [],
    nearby_place_ids: [],
    is_hidden_gem: false,
    is_heritage: false,
    is_unesco: false,
    family_friendly: false,
    nature_related: false,
    adventure_related: false,
    popularity: { popularity_score: 0, rating_average: null, rating_count: 0 },
    ...overrides,
  };
}

describe('catalog derivation helpers', () => {
  it('ranks popular destinations by popularity score descending', () => {
    const low = makeDestination({
      id: 'low',
      name: 'Low',
      popularity: { popularity_score: 0.2, rating_average: null, rating_count: 0 },
    });
    const high = makeDestination({
      id: 'high',
      name: 'High',
      popularity: { popularity_score: 0.9, rating_average: null, rating_count: 0 },
    });

    const result = selectPopularDestinations([low, high]);

    expect(result.map((d) => d.id)).toEqual(['high', 'low']);
  });

  it('selects hidden gems by flag or category', () => {
    const flagged = makeDestination({ id: 'flagged', is_hidden_gem: true });
    const byCategory = makeDestination({ id: 'by-category', category: 'hidden-gems' });
    const regular = makeDestination({ id: 'regular' });

    const result = selectHiddenGems([flagged, byCategory, regular]);

    expect(result.map((d) => d.id).sort()).toEqual(['by-category', 'flagged']);
  });

  it('recommends only rated destinations ordered by average rating', () => {
    const unrated = makeDestination({ id: 'unrated' });
    const good = makeDestination({
      id: 'good',
      popularity: { popularity_score: 0, rating_average: 4.2, rating_count: 10 },
    });
    const best = makeDestination({
      id: 'best',
      popularity: { popularity_score: 0, rating_average: 4.9, rating_count: 5 },
    });

    const result = selectRecommendedDestinations([unrated, good, best]);

    expect(result.map((d) => d.id)).toEqual(['best', 'good']);
  });

  it('groups popular cities and counts destinations', () => {
    const cities = selectPopularCities([
      makeDestination({ id: 'a', city: 'Madurai', district: 'madurai' }),
      makeDestination({ id: 'b', city: 'Madurai', district: 'madurai' }),
      makeDestination({ id: 'c', city: 'Chennai', district: 'chennai' }),
    ]);

    expect(cities[0]).toMatchObject({ city: 'Madurai', destinationCount: 2 });
    expect(cities.map((c) => c.city)).toContain('Chennai');
  });

  it('lists only categories present in the catalog, in vocabulary order', () => {
    const categories = selectCategories([
      makeDestination({ id: 'a', category: 'food' }),
      makeDestination({ id: 'b', category: 'temples' }),
    ]);

    expect(categories.map((c) => c.category)).toEqual(['temples', 'food']);
    expect(categories.find((c) => c.category === 'temples')?.destinationCount).toBe(1);
  });

  it('creates url-safe city slugs', () => {
    expect(citySlug('Tiruchirappalli')).toBe('tiruchirappalli');
    expect(citySlug('  The Nilgiris  ')).toBe('the-nilgiris');
  });

  it('reconstructs a searchable city name from a slug', () => {
    expect(deSlugCity('madurai')).toBe('madurai');
    expect(deSlugCity('the-nilgiris')).toBe('the nilgiris');
  });

  it('de-slugging a single-word city round-trips the slug case-insensitively', () => {
    expect(deSlugCity(citySlug('Madurai'))).toBe('madurai');
    expect(deSlugCity(citySlug('The Nilgiris'))).toBe('the nilgiris');
  });
});
