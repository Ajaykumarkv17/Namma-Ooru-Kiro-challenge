import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';

import type { CityView, Destination } from '../api/types';
import { CityPage } from './CityPage';

const { fetchCityViewMock } = vi.hoisted(() => ({
  fetchCityViewMock: vi.fn(),
}));

vi.mock('../api/client', () => ({
  fetchCityView: fetchCityViewMock,
  fetchDestinations: vi.fn(),
  fetchDestination: vi.fn(),
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

function makeCityView(overrides: Partial<CityView> = {}): CityView {
  return {
    city: 'Madurai',
    district: 'Madurai',
    region: 'South Tamil Nadu',
    destination_count: 1,
    sections: [
      {
        key: 'temples',
        title: 'Temples',
        destinations: [makeDestination()],
      },
    ],
    ...overrides,
  };
}

function renderPage(slug = 'madurai') {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[`/cities/${slug}`]}>
        <Routes>
          <Route element={<CityPage />} path="/cities/:citySlug" />
          <Route element={<div>Destination detail route</div>} path="/destinations/:id" />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

afterEach(() => {
  vi.clearAllMocks();
});

describe('CityPage (Requirement 2.1)', () => {
  it('shows a skeleton while loading', () => {
    fetchCityViewMock.mockReturnValue(new Promise(() => {}));
    renderPage();

    expect(screen.getAllByRole('status', { name: 'Loading city' }).length).toBeGreaterThan(0);
  });

  it('renders the city overview and grouped sections when records exist', async () => {
    fetchCityViewMock.mockResolvedValue(
      makeCityView({
        sections: [
          { key: 'popular', title: 'Popular Places', destinations: [makeDestination()] },
          { key: 'temples', title: 'Temples', destinations: [makeDestination()] },
        ],
        destination_count: 2,
      }),
    );
    renderPage();

    await waitFor(() =>
      expect(screen.getByRole('heading', { level: 1, name: 'Madurai' })).toBeInTheDocument(),
    );
    expect(screen.getByRole('heading', { name: 'Popular Places' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Temples' })).toBeInTheDocument();
    expect(screen.getByText(/Madurai · South Tamil Nadu/)).toBeInTheDocument();
  });

  it('links destinations within a section to their detail page (Requirement 2.4/1.5)', async () => {
    fetchCityViewMock.mockResolvedValue(makeCityView());
    renderPage();

    const section = await screen.findByRole('region', { name: 'Temples' });
    expect(within(section).getByRole('link', { name: /Meenakshi Amman Temple/ })).toHaveAttribute(
      'href',
      '/destinations/madurai-meenakshi-amman-temple',
    );
  });

  it('shows an empty state when the city has no catalogued sections', async () => {
    fetchCityViewMock.mockResolvedValue(
      makeCityView({
        city: 'Chennai',
        district: null,
        region: null,
        destination_count: 0,
        sections: [],
      }),
    );
    renderPage('chennai');

    await waitFor(() =>
      expect(screen.getByRole('heading', { name: 'Nothing here yet' })).toBeInTheDocument(),
    );
    expect(screen.getByRole('button', { name: 'Search destinations' })).toBeInTheDocument();
  });

  it('shows an accessible error state with retry when the request fails', async () => {
    fetchCityViewMock.mockRejectedValue(new Error('boom'));
    renderPage();

    await waitFor(() => expect(screen.getByRole('alert')).toBeInTheDocument());
    expect(screen.getByRole('button', { name: 'Try again' })).toBeInTheDocument();
  });

  it('de-slugs a multi-word city slug before requesting the view', async () => {
    fetchCityViewMock.mockResolvedValue(makeCityView({ city: 'The Nilgiris' }));
    renderPage('the-nilgiris');

    await waitFor(() => expect(fetchCityViewMock).toHaveBeenCalledWith('the nilgiris'));
  });
});
