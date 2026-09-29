import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';

import type { Destination, SearchIntent, SearchResult } from '../api/types';
import { SearchPage } from './SearchPage';

const { searchDestinationsMock } = vi.hoisted(() => ({
  searchDestinationsMock: vi.fn(),
}));

vi.mock('../api/client', () => ({
  searchDestinations: searchDestinationsMock,
  ApiError: class ApiError extends Error {},
}));

function makeDestination(overrides: Partial<Destination> = {}): Destination {
  return {
    id: 'madurai-meenakshi-amman-temple',
    name: 'Meenakshi Amman Temple',
    alternate_names: [],
    city: 'Madurai',
    district: 'Madurai',
    region: 'South Tamil Nadu',
    category: 'temples',
    subcategory: null,
    description: 'A historic temple in the heart of Madurai.',
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
    is_heritage: true,
    is_unesco: false,
    family_friendly: true,
    nature_related: false,
    adventure_related: false,
    popularity: { popularity_score: 0.9, rating_average: 4.8, rating_count: 120 },
    ...overrides,
  };
}

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

function makeResult(overrides: Partial<SearchResult> = {}): SearchResult {
  return {
    query: 'temples in madurai',
    intent: makeIntent({ location: 'Madurai', category: 'temples' }),
    filters: { city: 'Madurai', category: 'temples', tags: ['heritage'] },
    destinations: [makeDestination()],
    result_count: 1,
    used_fallback: false,
    fallback_reason: null,
    ...overrides,
  };
}

function renderPage(query = 'temples in madurai') {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const initial = query ? `/search?q=${encodeURIComponent(query)}` : '/search';
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[initial]}>
        <Routes>
          <Route element={<SearchPage />} path="/search" />
          <Route element={<div>Destination detail route</div>} path="/destinations/:id" />
          <Route element={<div>Home route</div>} path="/" />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

afterEach(() => {
  vi.clearAllMocks();
});

describe('SearchPage (Requirements 4.2, 4.3)', () => {
  it('renders structured results with active-filter chips and result count', async () => {
    searchDestinationsMock.mockResolvedValue(makeResult());
    renderPage();

    await waitFor(() =>
      expect(
        screen.getByRole('heading', { name: /1 place for “temples in madurai”/ }),
      ).toBeInTheDocument(),
    );

    // Active filters rendered as visible chips.
    const filters = screen.getByRole('region', { name: 'Active filters' });
    expect(within(filters).getByText('Madurai')).toBeInTheDocument();
    expect(within(filters).getByText('Temples')).toBeInTheDocument();
    expect(within(filters).getByText('heritage')).toBeInTheDocument();

    // Structured destination result reusing DestinationCard.
    expect(screen.getByRole('link', { name: /Meenakshi Amman Temple/ })).toHaveAttribute(
      'href',
      '/destinations/madurai-meenakshi-amman-temple',
    );

    // AI-derived interpretation is badged and separated from source results.
    const interpretation = screen.getByRole('region', { name: 'How we read your search' });
    expect(within(interpretation).getByText('AI interpretation')).toBeInTheDocument();
  });

  it('shows a loading skeleton while the search is in flight', () => {
    searchDestinationsMock.mockReturnValue(new Promise(() => {}));
    renderPage();

    expect(screen.getAllByRole('status', { name: 'Loading results' }).length).toBeGreaterThan(0);
  });

  it('shows an empty state when no destinations match', async () => {
    searchDestinationsMock.mockResolvedValue(
      makeResult({ destinations: [], result_count: 0, filters: {} }),
    );
    renderPage();

    await waitFor(() =>
      expect(screen.getByRole('heading', { name: 'No matches yet' })).toBeInTheDocument(),
    );
    expect(screen.getByRole('button', { name: 'Browse all destinations' })).toBeInTheDocument();
  });

  it('shows an accessible error state with retry when the search fails', async () => {
    searchDestinationsMock.mockRejectedValue(new Error('boom'));
    renderPage();

    await waitFor(() => expect(screen.getByRole('alert')).toBeInTheDocument());
    expect(screen.getByRole('button', { name: 'Try again' })).toBeInTheDocument();
  });

  it('surfaces an accessible fallback notice when used_fallback is true (Req 4.3)', async () => {
    searchDestinationsMock.mockResolvedValue(
      makeResult({
        used_fallback: true,
        fallback_reason: 'AI interpretation is temporarily unavailable; showing keyword matches.',
      }),
    );
    renderPage();

    const notice = await screen.findByRole('status', {
      name: 'Showing keyword and tag matches',
    });
    expect(
      within(notice).getByText(/AI interpretation is temporarily unavailable/),
    ).toBeInTheDocument();
  });

  it('shows a prompt and runs no search when the query is empty', () => {
    renderPage('');

    expect(screen.getByRole('heading', { name: 'Start your search' })).toBeInTheDocument();
    expect(searchDestinationsMock).not.toHaveBeenCalled();
  });

  it('submitting the controls runs a search for the new query', async () => {
    searchDestinationsMock.mockResolvedValue(makeResult());
    renderPage('');

    const user = userEvent.setup();
    await user.type(screen.getByRole('searchbox'), 'beaches in chennai');
    await user.click(screen.getByRole('button', { name: 'Search' }));

    await waitFor(() => expect(searchDestinationsMock).toHaveBeenCalledWith('beaches in chennai'));
  });
});
