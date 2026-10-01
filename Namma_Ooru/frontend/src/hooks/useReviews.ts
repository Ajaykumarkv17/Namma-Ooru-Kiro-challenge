/** React Query read/write hooks for destination visitor reviews. */

import { useMutation, useQuery, useQueryClient, type UseQueryResult } from '@tanstack/react-query';

import { createReview, fetchReviews } from '../api/client';
import type { Review, ReviewAggregate, ReviewCreateRequest } from '../api/types';

export function reviewsQueryKey(destinationId: string): readonly [string, string] {
  return ['reviews', destinationId];
}

export function useReviews(destinationId: string): UseQueryResult<ReviewAggregate> {
  return useQuery({
    queryKey: reviewsQueryKey(destinationId),
    queryFn: () => fetchReviews(destinationId),
    enabled: destinationId.length > 0,
  });
}

export function useCreateReview(destinationId: string) {
  const queryClient = useQueryClient();
  return useMutation<Review, Error, ReviewCreateRequest>({
    mutationFn: (payload) => createReview(destinationId, payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: reviewsQueryKey(destinationId) });
    },
  });
}
