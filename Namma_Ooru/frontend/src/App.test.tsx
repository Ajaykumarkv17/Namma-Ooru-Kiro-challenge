import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';

import type { Destination, DestinationDetail } from './api/types';
import { App } from './App';

const { fetchDestinationMock, fetchCityViewMock, fetchDestinationsMock } = vi.hoisted(() => ({
  fetchDestinationMock: vi.fn(),
  fetchCityViewMock: vi.fn(),
  fetchDestinationsMock: vi.fn(),
}));

vi.mock('./api/client', () => ({
  fetchDestination: fetchDestinationMock,
  fetchCityView: fetchCityViewMock,
  fetchDestinations: fetchDestinationsMock,
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

function renderApp(initialEntry: string) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[initialEntry]}>
        <App />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

afterEach(() => {
  vi.clearAllMocks();
});

describe('App routing', () => {
  it('renders the discovery route in the shared application layout', () => {
    fetchDestinationsMock.mockResolvedValue([]);
    renderApp('/');

    expect(
      screen.getByRole('heading', { name: 'Discover the Tamil Nadu you haven’t seen.' }),
    ).toBeInTheDocument();
    expect(screen.getByRole('navigation', { name: 'Primary navigation' })).toBeInTheDocument();
  });

  it('routes destination paths to the destination detail page', async () => {
    const detail: DestinationDetail = { destination: makeDestination(), nearby: [] };
    fetchDestinationMock.mockResolvedValue(detail);
    renderApp('/destinations/madurai-meenakshi-amman-temple');

    await waitFor(() =>
      expect(
        screen.getByRole('heading', { level: 1, name: 'Meenakshi Amman Temple' }),
      ).toBeInTheDocument(),
    );
    expect(fetchDestinationMock).toHaveBeenCalledWith('madurai-meenakshi-amman-temple');
  });

  it('routes city paths to the city guide page', async () => {
    fetchCityViewMock.mockResolvedValue({
      city: 'Madurai',
      district: 'Madurai',
      region: 'South Tamil Nadu',
      destination_count: 1,
      sections: [{ key: 'temples', title: 'Temples', destinations: [makeDestination()] }],
    });
    renderApp('/cities/madurai');

    await waitFor(() =>
      expect(screen.getByRole('heading', { level: 1, name: 'Madurai' })).toBeInTheDocument(),
    );
  });
});
