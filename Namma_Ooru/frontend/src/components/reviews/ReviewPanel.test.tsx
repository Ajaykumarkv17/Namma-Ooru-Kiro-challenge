import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { ReviewPanel } from './ReviewPanel';

const { createReviewMock, fetchReviewsMock } = vi.hoisted(() => ({
  createReviewMock: vi.fn(),
  fetchReviewsMock: vi.fn(),
}));

vi.mock('../../api/client', () => ({
  createReview: createReviewMock,
  fetchReviews: fetchReviewsMock,
}));

const aggregate = {
  destination_id: 'madurai-meenakshi-temple',
  review_count: 2,
  average_rating: 4,
  rating_distribution: { 1: 0, 2: 0, 3: 1, 4: 0, 5: 1 },
  ai_summary: {
    positives: ['Visitors praise the experience.'],
    concerns: ['Some visitors reported concerns.'],
    review_count: 2,
  },
  reviews: [
    {
      id: 'review-1',
      destination_id: 'madurai-meenakshi-temple',
      rating: 5,
      text: 'Magnificent temple complex.',
      tags: [],
      created_at: '2025-01-02T00:00:00Z',
    },
  ],
};

function renderPanel() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <ReviewPanel destinationId="madurai-meenakshi-temple" />
    </QueryClientProvider>,
  );
}

afterEach(() => vi.clearAllMocks());

describe('ReviewPanel', () => {
  it('renders aggregate, rating distribution, and recent reviews', async () => {
    fetchReviewsMock.mockResolvedValue(aggregate);
    renderPanel();

    expect(await screen.findByText('2 reviews')).toBeInTheDocument();
    expect(screen.getByLabelText('Rating distribution')).toBeInTheDocument();
    expect(screen.getByText('Magnificent temple complex.')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Recent reviews' })).toBeInTheDocument();
    expect(screen.getByText('AI summary')).toBeInTheDocument();
    expect(screen.getByText('Visitors praise the experience.')).toBeInTheDocument();
  });

  it('submits selected rating and optional review text', async () => {
    fetchReviewsMock.mockResolvedValue(aggregate);
    createReviewMock.mockResolvedValue(aggregate.reviews[0]);
    const user = userEvent.setup();
    renderPanel();

    await screen.findByText('2 reviews');
    await user.click(screen.getByLabelText('3 ★'));
    await user.type(screen.getByLabelText(/Review/), 'A thoughtful visit.');
    await user.click(screen.getByRole('button', { name: 'Submit review' }));

    await waitFor(() =>
      expect(createReviewMock).toHaveBeenCalledWith('madurai-meenakshi-temple', {
        rating: 3,
        text: 'A thoughtful visit.',
      }),
    );
  });

  it('renders an accessible error with retry when review loading fails', async () => {
    fetchReviewsMock.mockRejectedValue(new Error('offline'));
    renderPanel();

    expect(await screen.findByRole('alert')).toHaveTextContent('Reviews are unavailable');
    const retry = screen.getByRole('button', { name: 'Try again' });
    fireEvent.click(retry);
    await waitFor(() => expect(fetchReviewsMock).toHaveBeenCalledTimes(2));
  });

  it('renders submission errors accessibly', async () => {
    fetchReviewsMock.mockResolvedValue(aggregate);
    createReviewMock.mockRejectedValue(new Error('invalid'));
    const user = userEvent.setup();
    renderPanel();

    await screen.findByText('2 reviews');
    await user.click(screen.getByRole('button', { name: 'Submit review' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('could not submit your review');
  });
});
