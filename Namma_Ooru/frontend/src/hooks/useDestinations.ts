/**
 * React Query hooks for the catalog. All catalog reads flow through here so
 * components receive cached data with loading/error status and never call the API
 * client directly (Coding steering: data fetching via React Query only).
 */

import { useQuery, type UseQueryResult } from '@tanstack/react-query';

import { fetchCityView, fetchDestination, fetchDestinations } from '../api/client';
import type { CityView, Destination, DestinationDetail, DestinationFilters } from '../api/types';

/** Stable query key for a destinations query, keyed by its filters. */
export function destinationsQueryKey(filters?: DestinationFilters): readonly unknown[] {
  return ['destinations', filters ?? {}] as const;
}

/** Fetch the destination catalog, optionally filtered. */
export function useDestinations(filters?: DestinationFilters): UseQueryResult<Destination[]> {
  return useQuery({
    queryKey: destinationsQueryKey(filters),
    queryFn: () => fetchDestinations(filters),
  });
}

/** Fetch a single Destination with its resolved nearby places. */
export function useDestination(id: string): UseQueryResult<DestinationDetail> {
  return useQuery({
    queryKey: ['destination', id] as const,
    queryFn: () => fetchDestination(id),
    enabled: id.length > 0,
  });
}

/** Fetch a single city's grouped overview. */
export function useCityView(city: string): UseQueryResult<CityView> {
  return useQuery({
    queryKey: ['city', city] as const,
    queryFn: () => fetchCityView(city),
    enabled: city.length > 0,
  });
}
