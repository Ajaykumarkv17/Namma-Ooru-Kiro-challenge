import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';

import type { Destination, RecommendationResult, SurpriseRecommendation } from '../../api/types';
import { PersonalizedDiscovery } from './PersonalizedDiscovery';

const { getRecommendationsMock } = vi.hoisted(() => ({
  getRecommendationsMock: vi.fn(),
}));

vi.mock('../../api/client', () => ({
  getRecommendations: getRecommendationsMock,
  ApiError: class ApiError extends Error {},
}));

function makeDestination(overrides: Partial<Destination> = {}): Destination {
  return {
    id: 'ooty-botanical-garden',
    name: 'Ooty Botanical Garden',
    alternate_names: [],
    city: 'Ooty',
    district: 'The Nilgiris',
    region: 'West Tamil Nadu',
    category: 'nature',
    subcategory: null,
    description: 'Terraced gardens in the Nilgiri hills.',
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
    family_friendly: true,
    nature_related: true,
    adventure_related: false,
    popularity: { popularity_score: 0.7, rating_average: 4.5, rating_count: 40 },
    ...overrides,
  };
}

function makeSurprise(overrides: Partial<SurpriseRecommendation> = {}): SurpriseRecommendation {
  return {
    destination: makeDestination({
      id: 'hidden-village-trail',
      name: 'Hidden Village Trail',
      is_hidden_gem: true,
    }),
    category: 'hidden-gems',
    suggested_duration_minutes: 90,
    short_description: 'A quiet trail few travelers reach.',
    rationale: 'We picked this hidden-gems spot in Ooty because it rewards curious explorers.',
    rationale_is_ai_generated: true,
    ...overrides,
  };
}

function interestsResult(destinations: Destination[]): RecommendationResult {
  return {
    mode: 'interests',
    journey: null,
    interests: ['nature'],
    destinations,
    result_count: destinations.length,
    surprise: null,
  };
}

function renderDiscovery() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <PersonalizedDiscovery />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

afterEach(() => {
  vi.clearAllMocks();
});

describe('PersonalizedDiscovery', () => {
  it('prompts to choose interests before any fetch and stays disabled', () => {
    renderDiscovery();

    expect(
      screen.getByRole('heading', { level: 2, name: 'Discover your way' }),
    ).toBeInTheDocument();
    expect(screen.getByText(/Choose one or more interests/)).toBeInTheDocument();
    expect(getRecommendationsMock).not.toHaveBeenCalled();
  });

  it('fetches and renders matching destinations when an interest is selected (Req 8.1)', async () => {
    getRecommendationsMock.mockResolvedValue(interestsResult([makeDestination()]));
    const user = userEvent.setup();
    renderDiscovery();

    await user.click(screen.getByRole('button', { name: 'Nature' }));

    await waitFor(() =>
      expect(getRecommendationsMock).toHaveBeenCalledWith({
        mode: 'interests',
        interests: ['nature'],
      }),
    );
    const results = await screen.findByRole('region', { name: 'Matched to your interests' });
    expect(
      within(results).getByRole('link', { name: /Ooty Botanical Garden/ }),
    ).toBeInTheDocument();
  });

  it('shows a skeleton while an interest recommendation loads', async () => {
    getRecommendationsMock.mockReturnValue(new Promise(() => {}));
    const user = userEvent.setup();
    renderDiscovery();

    await user.click(screen.getByRole('button', { name: 'Temples' }));

    await waitFor(() =>
      expect(
        screen.getAllByRole('status', { name: 'Loading destinations' }).length,
      ).toBeGreaterThan(0),
    );
  });

  it('shows an empty state when a selection matches nothing', async () => {
    getRecommendationsMock.mockResolvedValue(interestsResult([]));
    const user = userEvent.setup();
    renderDiscovery();

    await user.click(screen.getByRole('button', { name: 'Beaches' }));

    expect(await screen.findByRole('heading', { name: 'Nothing here yet' })).toBeInTheDocument();
    expect(screen.getByText(/No destinations matched this selection/)).toBeInTheDocument();
  });

  it('shows an error state with retry when the request fails', async () => {
    getRecommendationsMock.mockRejectedValue(new Error('boom'));
    const user = userEvent.setup();
    renderDiscovery();

    await user.click(screen.getByRole('button', { name: 'Food' }));

    expect(await screen.findByRole('alert')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Try again' })).toBeInTheDocument();
  });

  it('fetches a themed journey by slug and renders its picks (Req 8.3)', async () => {
    getRecommendationsMock.mockResolvedValue({
      mode: 'journey',
      journey: 'hill-escape',
      interests: [],
      destinations: [makeDestination()],
      result_count: 1,
      surprise: null,
    } satisfies RecommendationResult);
    const user = userEvent.setup();
    renderDiscovery();

    await user.click(screen.getByRole('tab', { name: 'Themed journeys' }));
    await user.click(screen.getByRole('button', { name: /Hill Escape/ }));

    await waitFor(() =>
      expect(getRecommendationsMock).toHaveBeenCalledWith({
        mode: 'journey',
        journey: 'hill-escape',
      }),
    );
    expect(await screen.findByRole('heading', { name: 'Hill Escape picks' })).toBeInTheDocument();
  });

  it('reveals a Surprise Me pick with the AI rationale badged and separate from source facts (Req 8.2)', async () => {
    getRecommendationsMock.mockResolvedValue({
      mode: 'surprise',
      journey: null,
      interests: [],
      destinations: [],
      result_count: 0,
      surprise: makeSurprise(),
    } satisfies RecommendationResult);
    const user = userEvent.setup();
    renderDiscovery();

    await user.click(screen.getByRole('tab', { name: 'Surprise me' }));
    await user.click(screen.getByRole('button', { name: 'Surprise me' }));

    await waitFor(() =>
      expect(getRecommendationsMock).toHaveBeenCalledWith(
        expect.objectContaining({ mode: 'surprise' }),
      ),
    );

    // Source facts render from the destination record.
    expect(await screen.findByRole('link', { name: /Hidden Village Trail/ })).toBeInTheDocument();
    expect(screen.getByText('A quiet trail few travelers reach.')).toBeInTheDocument();

    // The AI rationale is badged "AI pick" and lives in its own labelled region,
    // separate from the source facts.
    const rationale = screen.getByRole('region', { name: 'Why we chose this for you' });
    expect(within(rationale).getByText('AI pick')).toBeInTheDocument();
    expect(within(rationale).getByText(/rewards curious explorers/)).toBeInTheDocument();
  });
});
