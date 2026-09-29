/**
 * Natural-language search results page (Requirements 4.2, 4.3). The Travel Query
 * is carried in the URL (`/search?q=...`) so it is shareable and survives reload;
 * submitting the controls updates the query param, which re-runs the cached
 * search via React Query. The page renders exactly one of content, skeleton
 * (loading), empty, or error (UI steering), and when the backend used keyword/tag
 * matching because the AI Provider was unavailable it shows an accessible
 * fallback notice (Requirement 4.3). AI-derived interpretation is badged and kept
 * separate from the source catalog results.
 */

import { useMemo } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';

import { DestinationGrid } from '../components/catalog/DestinationGrid';
import { ActiveFilterChips } from '../components/search/ActiveFilterChips';
import { FallbackNotice } from '../components/search/FallbackNotice';
import { SearchControls } from '../components/search/SearchControls';
import { SearchInterpretation } from '../components/search/SearchInterpretation';
import { EmptyState } from '../components/ui/EmptyState';
import { ErrorState } from '../components/ui/ErrorState';
import { Skeleton } from '../components/ui/Skeleton';
import { useSearch } from '../hooks/useSearch';
import { activeFilterChips, intentChips } from '../lib/search';

function ResultSkeletons() {
  return (
    <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
      {Array.from({ length: 8 }, (_, index) => (
        <Skeleton className="h-72" key={index} label="Loading results" />
      ))}
    </div>
  );
}

export function SearchPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const query = (searchParams.get('q') ?? '').trim();

  const result = useSearch(query);

  const filterChips = useMemo(
    () => (result.data ? activeFilterChips(result.data.filters) : []),
    [result.data],
  );
  const interpretationChips = useMemo(
    () => (result.data ? intentChips(result.data.intent) : []),
    [result.data],
  );

  const submitQuery = (next: string) => {
    setSearchParams({ q: next });
  };

  const state: 'idle' | 'loading' | 'error' | 'ready' =
    query.length === 0 ? 'idle' : result.isPending ? 'loading' : result.isError ? 'error' : 'ready';

  const destinations = result.data?.destinations ?? [];
  const resultCount = result.data?.result_count ?? destinations.length;

  return (
    <div className="space-y-8">
      <header>
        <p className="text-sm font-bold uppercase tracking-[0.18em] text-ochre">
          Plan your discovery
        </p>
        <h1 className="mt-2 font-display text-4xl font-bold leading-tight text-maroon sm:text-5xl">
          Search Tamil Nadu
        </h1>
        <p className="mt-3 max-w-2xl text-lg text-ink/70">
          Describe the trip you have in mind and we’ll match source-attributed places across every
          district.
        </p>
        <div className="mt-6">
          <SearchControls initialQuery={query} onSubmit={submitQuery} />
        </div>
      </header>

      {state === 'idle' ? (
        <EmptyState
          description="Try something like “temples and food in Madurai” or “hidden waterfalls near Coimbatore”."
          title="Start your search"
        />
      ) : null}

      {state === 'loading' ? (
        <div aria-busy="true" className="space-y-4">
          <Skeleton className="h-6 w-48" label="Loading results" />
          <ResultSkeletons />
        </div>
      ) : null}

      {state === 'error' ? (
        <ErrorState
          message="We could not run your search right now. Please check your connection and try again."
          onRetry={() => {
            void result.refetch();
          }}
        />
      ) : null}

      {state === 'ready' ? (
        <section aria-labelledby="search-results-heading" className="space-y-5">
          {result.data?.used_fallback ? (
            <FallbackNotice reason={result.data.fallback_reason} />
          ) : null}

          <SearchInterpretation chips={interpretationChips} headingId="search-interpretation" />

          <ActiveFilterChips chips={filterChips} headingId="search-active-filters" />

          <h2 className="font-display text-2xl font-bold text-maroon" id="search-results-heading">
            {resultCount} {resultCount === 1 ? 'place' : 'places'} for “{query}”
          </h2>

          {destinations.length > 0 ? (
            <DestinationGrid destinations={destinations} />
          ) : (
            <EmptyState
              action={
                <button
                  className="rounded-full bg-teal px-5 py-2.5 font-semibold text-white transition hover:bg-teal/90"
                  onClick={() => navigate('/')}
                  type="button"
                >
                  Browse all destinations
                </button>
              }
              description="No destinations matched this search. Try a different place, category, or interest."
              title="No matches yet"
            />
          )}
        </section>
      ) : null}
    </div>
  );
}
