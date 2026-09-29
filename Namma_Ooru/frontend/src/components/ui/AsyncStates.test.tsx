import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { EmptyState } from './EmptyState';
import { ErrorState } from './ErrorState';
import { Skeleton } from './Skeleton';

describe('shared async states', () => {
  it('exposes loading status to assistive technology', () => {
    render(<Skeleton className="h-20" label="Loading destinations" />);

    expect(screen.getByRole('status', { name: 'Loading destinations' })).toBeInTheDocument();
  });

  it('renders an empty-state discovery action', () => {
    render(
      <EmptyState
        action={<a href="/search">Explore destinations</a>}
        description="Try another part of Tamil Nadu."
        title="Nothing found yet"
      />,
    );

    expect(screen.getByRole('heading', { name: 'Nothing found yet' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Explore destinations' })).toHaveAttribute(
      'href',
      '/search',
    );
  });

  it('calls retry from an accessible error state', async () => {
    const retry = vi.fn();
    const user = userEvent.setup();
    render(<ErrorState message="Please check your connection and try again." onRetry={retry} />);

    expect(screen.getByRole('alert')).toHaveTextContent('Please check your connection');
    await user.click(screen.getByRole('button', { name: 'Try again' }));

    expect(retry).toHaveBeenCalledTimes(1);
  });
});
