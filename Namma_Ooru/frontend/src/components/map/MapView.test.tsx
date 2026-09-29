/**
 * Tests for the MapProvider-driven MapView (task 3.3).
 *
 * A mock `MapProvider` is injected so the tests never need a real WebGL canvas:
 * they assert the component drives the provider only through the interface
 * (mount + renderMarkers), that filters flow to the query, and that selecting a
 * marker shows an accessible preview with a real navigation link to the
 * Destination page (Requirement 9.3, 9.4). `fetchMapMarkers` is mocked at the
 * client boundary so no network is required.
 */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { act } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import type { MapMarker } from '../../api/types';
import * as client from '../../api/client';
import type { MapProvider, MapProviderMountOptions } from './MapProvider';
import { MapView } from './MapView';

function marker(overrides: Partial<MapMarker> = {}): MapMarker {
  return {
    id: 'madurai-meenakshi-temple',
    name: 'Meenakshi Temple',
    latitude: 9.9195,
    longitude: 78.1193,
    category: 'temples',
    city: 'Madurai',
    district: 'madurai',
    description: 'A landmark temple.',
    image_reference: null,
    is_hidden_gem: false,
    ...overrides,
  };
}

/** A mock provider that records interface calls and exposes marker selection. */
class MockMapProvider implements MapProvider {
  readonly name = 'Mock';
  mountCount = 0;
  destroyed = false;
  renderedMarkers: readonly MapMarker[] = [];
  private select: (m: MapMarker) => void = () => {};

  mount(options: MapProviderMountOptions): void {
    this.mountCount += 1;
    this.select = options.onMarkerSelect;
  }

  renderMarkers(markers: readonly MapMarker[]): void {
    this.renderedMarkers = markers;
  }

  destroy(): void {
    this.destroyed = true;
  }

  selectMarker(m: MapMarker): void {
    this.select(m);
  }
}

function renderMapView(provider: MapProvider) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <MapView providerFactory={() => provider} />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('MapView', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('mounts the provider and pushes fetched markers through the interface', async () => {
    const provider = new MockMapProvider();
    vi.spyOn(client, 'fetchMapMarkers').mockResolvedValue([marker()]);

    renderMapView(provider);

    await waitFor(() => expect(provider.renderedMarkers).toHaveLength(1));
    expect(provider.mountCount).toBe(1);
    expect(provider.renderedMarkers[0]?.id).toBe('madurai-meenakshi-temple');
  });

  it('shows a preview with a destination navigation link when a marker is selected', async () => {
    const provider = new MockMapProvider();
    vi.spyOn(client, 'fetchMapMarkers').mockResolvedValue([marker()]);
    const user = userEvent.setup();

    renderMapView(provider);

    const listButton = await screen.findByRole('button', { name: /Meenakshi Temple/ });
    await user.click(listButton);

    const preview = screen.getByRole('complementary', { name: 'Meenakshi Temple' });
    const link = within(preview).getByRole('link', { name: /View destination/ });
    expect(link).toHaveAttribute('href', '/destinations/madurai-meenakshi-temple');
  });

  it('surfaces selection triggered by the provider itself', async () => {
    const provider = new MockMapProvider();
    vi.spyOn(client, 'fetchMapMarkers').mockResolvedValue([marker()]);

    renderMapView(provider);

    await waitFor(() => expect(provider.renderedMarkers).toHaveLength(1));
    act(() => provider.selectMarker(marker()));

    const preview = await screen.findByRole('complementary', { name: 'Meenakshi Temple' });
    expect(within(preview).getByRole('link', { name: /View destination/ })).toBeInTheDocument();
  });

  it('applies the category filter to the marker query', async () => {
    const provider = new MockMapProvider();
    const fetchSpy = vi.spyOn(client, 'fetchMapMarkers').mockResolvedValue([marker()]);
    const user = userEvent.setup();

    renderMapView(provider);
    await waitFor(() => expect(fetchSpy).toHaveBeenCalled());

    await user.selectOptions(screen.getByRole('combobox', { name: 'Category' }), 'temples');

    await waitFor(() =>
      expect(fetchSpy).toHaveBeenCalledWith(expect.objectContaining({ category: 'temples' })),
    );
  });

  it('renders an empty state when no markers match', async () => {
    const provider = new MockMapProvider();
    vi.spyOn(client, 'fetchMapMarkers').mockResolvedValue([]);

    renderMapView(provider);

    expect(
      await screen.findByRole('heading', { name: 'No places on the map' }),
    ).toBeInTheDocument();
  });

  it('renders an error state when the marker query fails', async () => {
    const provider = new MockMapProvider();
    vi.spyOn(client, 'fetchMapMarkers').mockRejectedValue(new Error('boom'));

    renderMapView(provider);

    expect(await screen.findByRole('alert')).toHaveTextContent('map markers');
  });
});
