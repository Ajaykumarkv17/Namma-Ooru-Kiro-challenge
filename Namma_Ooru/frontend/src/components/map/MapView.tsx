/**
 * Interactive Tamil Nadu map (Requirement 9).
 *
 * `MapView` accesses map rendering *only* through the `MapProvider` interface
 * (Requirement 9.4): it mounts a provider into a container ref, hands it the
 * markers returned by `useMapMarkers`, and reacts to marker selection by showing
 * an accessible `MarkerPreview` with a navigation action to the Destination page
 * (Requirement 9.3). City and category filters drive the query (Requirement 9.2),
 * and every data-driven state renders content / skeleton / empty / error.
 *
 * The provider is injectable (`providerFactory`) so tests supply a mock provider
 * and never need a real WebGL canvas. Because plotting happens in the (mocked)
 * provider, an accessible marker list is also rendered so keyboard and
 * screen-reader users can select any marker without depending on the canvas.
 */

import { useEffect, useMemo, useRef, useState } from 'react';

import type { DestinationCategory, MapFilters, MapMarker } from '../../api/types';
import { useMapMarkers } from '../../hooks/useMapMarkers';
import { CATEGORY_LABELS } from '../../lib/catalog';
import { EmptyState } from '../ui/EmptyState';
import { ErrorState } from '../ui/ErrorState';
import { SectionHeader } from '../ui/SectionHeader';
import { Skeleton } from '../ui/Skeleton';
import {
  defaultMapProviderFactory,
  type MapProviderFactory,
  TAMIL_NADU_VIEWPORT,
} from './MapProvider';
import { MarkerPreview } from './MarkerPreview';

type MapViewProps = {
  /** Optional starting filters (e.g. a city page can scope the map to its city). */
  initialFilters?: MapFilters;
  /**
   * Provider factory — defaults to MapLibre GL. Tests inject a mock so no real
   * WebGL canvas is required.
   */
  providerFactory?: MapProviderFactory;
};

const CATEGORY_OPTIONS = Object.entries(CATEGORY_LABELS) as [DestinationCategory, string][];

export function MapView({
  initialFilters,
  providerFactory = defaultMapProviderFactory,
}: MapViewProps) {
  const [city, setCity] = useState(initialFilters?.city ?? '');
  const [category, setCategory] = useState<DestinationCategory | ''>(
    initialFilters?.category ?? '',
  );
  const [selected, setSelected] = useState<MapMarker | null>(null);

  const filters = useMemo<MapFilters>(() => {
    const next: MapFilters = {};
    if (city.trim()) {
      next.city = city.trim();
    }
    if (category) {
      next.category = category;
    }
    return next;
  }, [city, category]);

  const { data, isPending, isError, refetch } = useMapMarkers(filters);
  const markers = useMemo(() => data ?? [], [data]);

  const containerRef = useRef<HTMLDivElement>(null);
  const providerRef = useRef<ReturnType<MapProviderFactory> | null>(null);

  // Mount the provider once against the container, and tear it down on unmount.
  useEffect(() => {
    const container = containerRef.current;
    if (!container) {
      return;
    }
    const provider = providerFactory();
    providerRef.current = provider;
    void provider.mount({
      container,
      viewport: TAMIL_NADU_VIEWPORT,
      onMarkerSelect: setSelected,
    });
    return () => {
      provider.destroy();
      providerRef.current = null;
    };
  }, [providerFactory]);

  // Push the current marker set to the provider whenever it changes.
  useEffect(() => {
    providerRef.current?.renderMarkers(markers);
  }, [markers]);

  // A filter change can drop the previously selected marker; clear the preview
  // when the selection is no longer part of the rendered set.
  useEffect(() => {
    if (selected && !markers.some((marker) => marker.id === selected.id)) {
      setSelected(null);
    }
  }, [markers, selected]);

  return (
    <section aria-labelledby="map-heading" className="flex flex-col gap-5">
      <SectionHeader
        eyebrow="Explore by place"
        headingId="map-heading"
        title="Find destinations on the map"
      />

      <div className="flex flex-wrap gap-4">
        <label className="flex flex-col gap-1 text-sm font-semibold text-maroon">
          City
          <input
            className="rounded-full border border-gold/40 px-4 py-2 font-normal text-ink"
            onChange={(event) => setCity(event.target.value)}
            placeholder="Any city"
            type="text"
            value={city}
          />
        </label>
        <label className="flex flex-col gap-1 text-sm font-semibold text-maroon">
          Category
          <select
            className="rounded-full border border-gold/40 px-4 py-2 font-normal text-ink"
            onChange={(event) => setCategory(event.target.value as DestinationCategory | '')}
            value={category}
          >
            <option value="">Any category</option>
            {CATEGORY_OPTIONS.map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div
        aria-label="Interactive map of Tamil Nadu destinations"
        className="h-80 w-full overflow-hidden rounded-2xl border border-gold/30 bg-ochre/10"
        ref={containerRef}
        role="application"
      />

      {isPending ? (
        <Skeleton className="h-24" label="Loading map markers" />
      ) : isError ? (
        <ErrorState
          message="We could not load map markers right now."
          onRetry={() => void refetch()}
        />
      ) : markers.length === 0 ? (
        <EmptyState
          description="No destinations match these filters yet. Try a different city or category."
          title="No places on the map"
        />
      ) : (
        <div className="flex flex-col gap-4 md:flex-row md:items-start">
          <nav aria-label="Map destinations" className="md:w-1/2">
            <ul className="flex flex-col gap-2">
              {markers.map((marker) => (
                <li key={marker.id}>
                  <button
                    aria-pressed={selected?.id === marker.id}
                    className="w-full rounded-xl border border-gold/30 bg-white px-4 py-3 text-left transition hover:border-ochre focus-visible:border-ochre"
                    onClick={() => setSelected(marker)}
                    type="button"
                  >
                    <span className="font-display font-semibold text-maroon">{marker.name}</span>
                    <span className="block text-sm text-ink/70">
                      {marker.city}, {marker.district}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </nav>
          <div className="md:w-1/2">
            {selected ? (
              <MarkerPreview marker={selected} onClose={() => setSelected(null)} />
            ) : (
              <EmptyState
                description="Select a marker to preview it and open its destination page."
                title="Select a destination"
              />
            )}
          </div>
        </div>
      )}
    </section>
  );
}
