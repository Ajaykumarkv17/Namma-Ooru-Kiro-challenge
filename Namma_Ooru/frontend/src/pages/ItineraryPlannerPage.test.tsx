import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { ItineraryPlannerPage } from './ItineraryPlannerPage';

const { createItineraryMock, editItineraryMock } = vi.hoisted(() => ({
  createItineraryMock: vi.fn(),
  editItineraryMock: vi.fn(),
}));

vi.mock('../api/client', () => ({
  createItinerary: createItineraryMock,
  editItinerary: editItineraryMock,
}));

function renderPlanner() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <ItineraryPlannerPage />
    </QueryClientProvider>,
  );
}

describe('ItineraryPlannerPage', () => {
  it('renders a labelled AI itinerary timeline after generating a plan', async () => {
    createItineraryMock.mockResolvedValue({
      id: 'trip-1',
      destination_context: 'Madurai',
      allow_repeats: false,
      constraints: {},
      days: [
        {
          day_number: 1,
          activities: [
            {
              destination_id: 'madurai-temple',
              start_minute: 540,
              duration_minutes: 90,
              rationale: 'A calm start.',
              travel_context: 'Walkable area.',
              break_suggestion: 'Tea break.',
            },
          ],
        },
      ],
    });
    renderPlanner();
    fireEvent.click(screen.getByRole('button', { name: 'Create itinerary' }));

    await waitFor(() => expect(screen.getByText('AI itinerary')).toBeInTheDocument());
    expect(screen.getByText('madurai temple')).toBeInTheDocument();
    expect(screen.getByLabelText('Itinerary edit request')).toBeInTheDocument();
  });
});
