import { describe, expect, it } from 'vitest';

import type { DestinationFilters, SearchIntent } from '../api/types';
import { activeFilterChips, intentChips } from './search';

function makeIntent(overrides: Partial<SearchIntent> = {}): SearchIntent {
  return {
    location: null,
    duration_days: null,
    category: null,
    interests: [],
    travel_style: null,
    budget: null,
    group_context: null,
    ...overrides,
  };
}

describe('activeFilterChips', () => {
  it('returns no chips for unconstrained filters', () => {
    expect(activeFilterChips({})).toEqual([]);
    expect(activeFilterChips({ tags: [] })).toEqual([]);
  });

  it('labels category slugs with their display label', () => {
    const filters: DestinationFilters = { category: 'hidden-gems' };
    expect(activeFilterChips(filters)).toEqual([
      { key: 'category', label: 'Category', value: 'Hidden Gems' },
    ]);
  });

  it('renders one chip per tag and includes set boolean flags', () => {
    const filters: DestinationFilters = {
      city: 'Madurai',
      tags: ['heritage', 'food'],
      family_friendly: true,
      hidden_gems: false,
    };
    const chips = activeFilterChips(filters);
    expect(chips.map((c) => c.value)).toEqual(['Madurai', 'heritage', 'food', 'Families']);
    // hidden_gems is false, so it produces no chip.
    expect(chips.some((c) => c.key === 'hidden_gems')).toBe(false);
  });
});

describe('intentChips', () => {
  it('returns no chips when the model recognized nothing', () => {
    expect(intentChips(makeIntent())).toEqual([]);
  });

  it('pluralizes duration and includes each interest', () => {
    const chips = intentChips(
      makeIntent({ duration_days: 1, interests: ['temples', 'food'], location: 'Madurai' }),
    );
    expect(chips.find((c) => c.key === 'duration')?.value).toBe('1 day');
    expect(chips.filter((c) => c.label === 'Interest').map((c) => c.value)).toEqual([
      'temples',
      'food',
    ]);
    expect(chips.find((c) => c.key === 'location')?.value).toBe('Madurai');
  });

  it('uses plural days for multi-day durations', () => {
    const chips = intentChips(makeIntent({ duration_days: 3 }));
    expect(chips.find((c) => c.key === 'duration')?.value).toBe('3 days');
  });
});
