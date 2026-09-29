/**
 * A data-driven catalog section that renders exactly one of: content, skeleton
 * (loading), empty state, or error state (UI/UX steering). It owns the shared
 * async-state wiring so every home-page section behaves consistently.
 */

import type { ReactNode } from 'react';

import { EmptyState } from '../ui/EmptyState';
import { ErrorState } from '../ui/ErrorState';
import { SectionHeader } from '../ui/SectionHeader';
import { Skeleton } from '../ui/Skeleton';

type CatalogSectionState = 'loading' | 'error' | 'ready';

type CatalogSectionProps = {
  title: string;
  eyebrow?: string;
  description?: string;
  headingId: string;
  action?: ReactNode;
  state: CatalogSectionState;
  /** True when, after a successful load, the section has no matching records. */
  isEmpty: boolean;
  onRetry?: () => void;
  /** Text for the empty-state discovery action; omit to hide the action. */
  emptyActionLabel?: string;
  emptyDescription?: string;
  onEmptyAction?: () => void;
  /** Number of skeleton cards to show while loading. */
  skeletonCount?: number;
  children: ReactNode;
};

function SkeletonGrid({ count }: { count: number }) {
  return (
    <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
      {Array.from({ length: count }, (_, index) => (
        <Skeleton className="h-72" key={index} label="Loading destinations" />
      ))}
    </div>
  );
}

export function CatalogSection({
  title,
  eyebrow,
  description,
  headingId,
  action,
  state,
  isEmpty,
  onRetry,
  emptyActionLabel,
  emptyDescription = 'Explore another part of Tamil Nadu to keep discovering.',
  onEmptyAction,
  skeletonCount = 4,
  children,
}: CatalogSectionProps) {
  return (
    <section aria-labelledby={headingId} className="mt-12 first:mt-0">
      <SectionHeader
        action={action}
        description={description}
        eyebrow={eyebrow}
        headingId={headingId}
        title={title}
      />
      {state === 'loading' ? <SkeletonGrid count={skeletonCount} /> : null}
      {state === 'error' ? (
        <ErrorState
          message="We could not load this section. Please check your connection and try again."
          onRetry={onRetry}
        />
      ) : null}
      {state === 'ready' && isEmpty ? (
        <EmptyState
          action={
            emptyActionLabel && onEmptyAction ? (
              <button
                className="rounded-full bg-teal px-5 py-2.5 font-semibold text-white transition hover:bg-teal/90"
                onClick={onEmptyAction}
                type="button"
              >
                {emptyActionLabel}
              </button>
            ) : undefined
          }
          description={emptyDescription}
          title="Nothing here yet"
        />
      ) : null}
      {state === 'ready' && !isEmpty ? children : null}
    </section>
  );
}
