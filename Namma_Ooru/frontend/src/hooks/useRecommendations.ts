/**
 * React Query hook for personalized and themed discovery (Requirement 8). Interest,
 * themed-journey, and Surprise Me selections all resolve through `POST
 * /api/recommendations`, run as a cached query keyed by the active request and
 * disabled until the traveler makes a selection. All network I/O stays in the
 * client layer — components never call `getRecommendations` directly (Coding
 * steering: fetch through React Query).
 */

import { useQuery, type UseQueryResult } from '@tanstack/react-query';

import { getRecommendations } from '../api/client';
import type { RecommendationRequest, RecommendationResult } from '../api/types';

/** Stable query key for a recommendation request. */
export function recommendationsQueryKey(request: RecommendationRequest | null): readonly unknown[] {
  return ['recommendations', request ?? {}] as const;
}

/**
 * Fetch recommendations for the active request. A `null` request keeps the query
 * disabled so no call is made until the traveler picks interests, a journey, or
 * Surprise Me. Surprise Me re-rolls by passing a fresh `seed`, which changes the
 * query key and triggers a new pick.
 */
export function useRecommendations(
  request: RecommendationRequest | null,
): UseQueryResult<RecommendationResult> {
  return useQuery({
    queryKey: recommendationsQueryKey(request),
    queryFn: () => getRecommendations(request as RecommendationRequest),
    enabled: request !== null,
  });
}
