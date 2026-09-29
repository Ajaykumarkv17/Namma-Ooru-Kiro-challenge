import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';

import type { Destination } from '../api/types';
import { HomePage } from './HomePage';

const { fetchDestinationsMock } = vi.hoisted(() => ({
  fetchDestinationsMock: vi.fn(),
}));

vi.mock('../api/client', () => ({
  fetchDestinations: fetchDestinationsMock,
  fetchCityView: vi.fn(),
  ApiError: class ApiError extends Error {},
}));

function makeDestination(overrides: Partial<Destination> = {}): Destination {
  return {
    id: 'madurai-meenakshi-amman-temple',
    name: 'Meenakshi Amman Temple',
    alternate_names: [],
    city: 'Madurai',
    district: 'madurai',
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

function renderHome() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/']}>
        <Routes>
          <Route element={<HomePage />} path="/" />
          <Route element={<div>Destination detail route</div>} path="/destinations/:id" />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

afterEach(() => {
  vi.clearAllMocks();
});

describe('HomePage', () => {
  it('renders the hero, search control, and Explore Tamil Nadu call to action', async () => {
    fetchDestinationsMock.mockResolvedValue([makeDestination()]);
    renderHome();

    expect(
      screen.getByRole('heading', { level: 1, name: 'Discover the Tamil Nadu you haven’t seen.' }),
    ).toBeInTheDocument();
    expect(screen.getByRole('search', { name: 'Search destinations' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Explore Tamil Nadu/ })).toBeInTheDocument();

    await waitFor(() =>
      expect(screen.getByRole('heading', { name: 'Popular destinations' })).toBeInTheDocument(),
    );
  });

  it('shows skeleton content for sections while loading', () => {
    fetchDestinationsMock.mockReturnValue(new Promise(() => {}));
    renderHome();

    expect(screen.getAllByRole('status', { name: 'Loading destinations' }).length).toBeGreaterThan(
      0,
    );
  });

  it('renders catalog sections from the API once loaded', async () => {
    fetchDestinationsMock.mockResolvedValue([makeDestination()]);
    renderHome();

    await waitFor(() =>
      expect(screen.getByRole('heading', { name: 'Popular destinations' })).toBeInTheDocument(),
    );
    expect(screen.getByRole('heading', { name: 'Popular cities' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Browse by category' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Recommended for you' })).toBeInTheDocument();

    const popular = screen.getByRole('region', { name: 'Popular destinations' });
    expect(within(popular).getByRole('link', { name: /Meenakshi Amman Temple/ })).toHaveAttribute(
      'href',
      '/destinations/madurai-meenakshi-amman-temple',
    );
  });

  it('shows an empty state with a discovery action when a section has no records', async () => {
    fetchDestinationsMock.mockResolvedValue([]);
    renderHome();

    await waitFor(() =>
      expect(screen.getAllByRole('heading', { name: 'Nothing here yet' }).length).toBeGreaterThan(
        0,
      ),
    );
    expect(screen.getAllByRole('button', { name: 'Search destinations' }).length).toBeGreaterThan(
      0,
    );
  });

  it('shows an error state with retry when the catalog request fails', async () => {
    fetchDestinationsMock.mockRejectedValue(new Error('boom'));
    renderHome();

    await waitFor(() => expect(screen.getAllByRole('alert').length).toBeGreaterThan(0));
    expect(screen.getAllByRole('button', { name: 'Try again' }).length).toBeGreaterThan(0);
  });
});
