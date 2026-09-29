import { describe, expect, it } from 'vitest';

import {
  formatSuggestedDuration,
  JOURNEY_OPTIONS,
  journeyLabel,
  toggleInterest,
} from './recommendations';

describe('JOURNEY_OPTIONS', () => {
  it('exposes the eight named themed journeys with the exact display labels', () => {
    expect(JOURNEY_OPTIONS.map((option) => option.slug)).toEqual([
      'spiritual-journey',
      'hill-escape',
      'coastal-escape',
      'food-trail',
      'heritage-journey',
      'nature-escape',
      'photography-trip',
      'hidden-gems',
    ]);
    expect(JOURNEY_OPTIONS.map((option) => option.label)).toEqual([
      'Spiritual Journey',
      'Hill Escape',
      'Coastal Escape',
      'Food Trail',
      'Heritage Journey',
      'Nature Escape',
      'Photography Trip',
      'Hidden Gems',
    ]);
  });
});

describe('journeyLabel', () => {
  it('maps a slug to its display label', () => {
    expect(journeyLabel('spiritual-journey')).toBe('Spiritual Journey');
    expect(journeyLabel('hidden-gems')).toBe('Hidden Gems');
  });
});

describe('toggleInterest', () => {
  it('adds an absent interest, preserving order and without mutating', () => {
    const selected = ['temples'];
    const next = toggleInterest(selected, 'food');
    expect(next).toEqual(['temples', 'food']);
    expect(selected).toEqual(['temples']);
  });

  it('removes a present interest', () => {
    expect(toggleInterest(['temples', 'food'], 'temples')).toEqual(['food']);
  });
});

describe('formatSuggestedDuration', () => {
  it('returns null for unavailable or non-positive durations', () => {
    expect(formatSuggestedDuration(null)).toBeNull();
    expect(formatSuggestedDuration(0)).toBeNull();
    expect(formatSuggestedDuration(-30)).toBeNull();
  });

  it('formats hours and minutes with correct pluralization', () => {
    expect(formatSuggestedDuration(60)).toBe('1 hour');
    expect(formatSuggestedDuration(90)).toBe('1 hour 30 minutes');
    expect(formatSuggestedDuration(150)).toBe('2 hours 30 minutes');
    expect(formatSuggestedDuration(45)).toBe('45 minutes');
    expect(formatSuggestedDuration(1)).toBe('1 minute');
  });
});
