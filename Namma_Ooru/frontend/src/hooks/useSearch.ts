/**
 * React Query hook for natural-language search (Requirement 4). The Travel Query
 * arrives via the URL (`/search?q=...`), so the search runs as a cached query
 * keyed by the trimmed query string and stays disabled until a non-empty query is
 * present. All network I/O stays in the client layer — components never call
 * `searchDestinations` directly (Coding steering: fetch through React Query).
 */

import { useQuery, type UseQueryResult } from '@tanstack/react-query';

import { searchDestinations } from '../api/client';
import type { SearchResult } from '../api/types';

/** Stable query key for a search, keyed by its trimmed query string. */
export function searchQueryKey(query: string): readonly unknown[] {
  return ['search', query] as const;
}

/**
 * Run a natural-language search for the given query. The query is trimmed before
 * use; an empty query keeps the request disabled so no call is made until the
 * traveler submits a real query.
 */
export function useSearch(query: string): UseQueryResult<SearchResult> {
  const trimmed = query.trim();
  return useQuery({
    queryKey: searchQueryKey(trimmed),
    queryFn: () => searchDestinations(trimmed),
    enabled: trimmed.length > 0,
  });
}
