import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';

import type { Destination, DestinationDetail } from '../api/types';
import { DestinationPage } from './DestinationPage';

const { fetchDestinationMock } = vi.hoisted(() => ({
  fetchDestinationMock: vi.fn(),
}));

vi.mock('../api/client', () => ({
  fetchDestination: fetchDestinationMock,
  fetchDestinations: vi.fn(),
  fetchCityView: vi.fn(),
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

function renderPage(id = 'madurai-meenakshi-amman-temple') {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[`/destinations/${id}`]}>
        <Routes>
          <Route element={<DestinationPage />} path="/destinations/:destinationId" />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

afterEach(() => {
  vi.clearAllMocks();
});

describe('DestinationPage', () => {
  it('shows a skeleton while loading', () => {
    fetchDestinationMock.mockReturnValue(new Promise(() => {}));
    renderPage();

    expect(screen.getAllByRole('status', { name: 'Loading destination' }).length).toBeGreaterThan(
      0,
    );
  });

  it('shows an accessible error state with retry when the request fails', async () => {
    fetchDestinationMock.mockRejectedValue(new Error('boom'));
    renderPage();

    await waitFor(() => expect(screen.getByRole('alert')).toBeInTheDocument());
    expect(screen.getByRole('button', { name: 'Try again' })).toBeInTheDocument();
  });

  it('renders description, category, rating and available fields (Requirement 2.2)', async () => {
    const detail: DestinationDetail = {
      destination: makeDestination({
        best_time_to_visit: 'November to February',
        recommended_duration_minutes: 90,
        source_urls: ['https://tamilnadutourism.tn.gov.in/meenakshi'],
      }),
      nearby: [],
    };
    fetchDestinationMock.mockResolvedValue(detail);
    renderPage();

    await waitFor(() =>
      expect(
        screen.getByRole('heading', { level: 1, name: 'Meenakshi Amman Temple' }),
      ).toBeInTheDocument(),
    );
    expect(screen.getByText('A historic temple in the heart of Madurai.')).toBeInTheDocument();
    expect(screen.getByText('Temples')).toBeInTheDocument();
    expect(screen.getByText('November to February')).toBeInTheDocument();
    expect(screen.getByText('1 hour 30 min')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'tamilnadutourism.tn.gov.in' })).toHaveAttribute(
      'href',
      'https://tamilnadutourism.tn.gov.in/meenakshi',
    );
  });

  it('renders "Information unavailable" for null fields (Requirement 2.3)', async () => {
    fetchDestinationMock.mockResolvedValue({ destination: makeDestination(), nearby: [] });
    renderPage();

    await waitFor(() => expect(screen.getByRole('heading', { level: 1 })).toBeInTheDocument());
    // best time, duration, opening hours, entry fee, address, website, sources
    expect(screen.getAllByText('Information unavailable').length).toBeGreaterThanOrEqual(6);
  });

  it('links nearby places to their destination page (Requirement 2.4)', async () => {
    const detail: DestinationDetail = {
      destination: makeDestination(),
      nearby: [
        makeDestination({
          id: 'madurai-thirumalai-nayakkar-mahal',
          name: 'Thirumalai Nayakkar Mahal',
        }),
      ],
    };
    fetchDestinationMock.mockResolvedValue(detail);
    renderPage();

    const nearby = await screen.findByRole('region', { name: 'Nearby places' });
    expect(within(nearby).getByRole('link', { name: /Thirumalai Nayakkar Mahal/ })).toHaveAttribute(
      'href',
      '/destinations/madurai-thirumalai-nayakkar-mahal',
    );
  });

  it('badges the AI summary area separately from source content', async () => {
    fetchDestinationMock.mockResolvedValue({ destination: makeDestination(), nearby: [] });
    renderPage();

    await waitFor(() => expect(screen.getByText('AI summary')).toBeInTheDocument());
  });

  it('retries the request when the error retry button is clicked', async () => {
    fetchDestinationMock.mockRejectedValueOnce(new Error('boom'));
    fetchDestinationMock.mockResolvedValueOnce({
      destination: makeDestination(),
      nearby: [],
    });
    const user = userEvent.setup();
    renderPage();

    await waitFor(() => expect(screen.getByRole('alert')).toBeInTheDocument());
    await user.click(screen.getByRole('button', { name: 'Try again' }));

    await waitFor(() => expect(screen.getByRole('heading', { level: 1 })).toBeInTheDocument());
  });
});
