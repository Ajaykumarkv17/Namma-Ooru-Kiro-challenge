import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';

import { App } from './App';

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

describe('App routing', () => {
  it('renders the discovery route in the shared application layout', () => {
    renderApp('/');

    expect(
      screen.getByRole('heading', { name: 'Discover the Tamil Nadu you haven’t seen.' }),
    ).toBeInTheDocument();
    expect(screen.getByRole('navigation', { name: 'Primary navigation' })).toBeInTheDocument();
  });

  it('routes destination paths to the destination foundation page', () => {
    renderApp('/destinations/madurai-meenakshi-amman-temple');

    expect(screen.getByRole('heading', { name: 'Explore a destination.' })).toBeInTheDocument();
  });
});
