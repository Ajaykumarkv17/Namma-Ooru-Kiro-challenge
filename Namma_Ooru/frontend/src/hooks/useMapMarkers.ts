/**
 * React Query hook for the interactive map's markers. All marker reads flow
 * through here so `MapView` receives cached data with loading/error status and
 * never calls the API client directly (Coding steering: data fetching via React
 * Query only).
 */

import { useQuery, type UseQueryResult } from '@tanstack/react-query';

import { fetchMapMarkers } from '../api/client';
import type { MapFilters, MapMarker } from '../api/types';

/** Stable query key for a map-markers query, keyed by its active filters. */
export function mapMarkersQueryKey(filters?: MapFilters): readonly unknown[] {
  return ['map-markers', filters ?? {}] as const;
}

/** Fetch the map markers for the active city/category filters. */
export function useMapMarkers(filters?: MapFilters): UseQueryResult<MapMarker[]> {
  return useQuery({
    queryKey: mapMarkersQueryKey(filters),
    queryFn: () => fetchMapMarkers(filters),
  });
}
