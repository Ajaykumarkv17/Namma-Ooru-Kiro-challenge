/**
 * City guide page (Requirement 2.1). Renders a city overview and the grouped
 * Destination sections the backend assembles — popular places, temples, heritage,
 * food, nature/nearby attractions, and hidden gems — showing a section only when
 * matching records exist. All data comes from `GET /api/cities/{city}` via React
 * Query; the whole page renders exactly one of content, skeleton, empty, or error.
 */

import { useMemo } from 'react';
import { useNavigate, useParams } from 'react-router-dom';

import { CatalogSection } from '../components/catalog/CatalogSection';
import { DestinationGrid } from '../components/catalog/DestinationGrid';
import { SectionHeader } from '../components/ui/SectionHeader';
import { Skeleton } from '../components/ui/Skeleton';
import { useCityView } from '../hooks/useDestinations';
import { deSlugCity } from '../lib/catalog';

export function CityPage() {
  const { citySlug } = useParams<{ citySlug: string }>();
  const navigate = useNavigate();
  const cityQuery = deSlugCity(citySlug ?? '');
  const query = useCityView(cityQuery);

  const view = query.data;
  const sections = useMemo(() => view?.sections ?? [], [view]);

  const state: 'loading' | 'error' | 'ready' = query.isPending
    ? 'loading'
    : query.isError
      ? 'error'
      : 'ready';

  const retry = () => {
    void query.refetch();
  };
  const goToSearch = () => navigate('/search');

  const cityName = view?.city ?? cityQuery;
  const hasSections = sections.length > 0;

  return (
    <div className="space-y-10">
      <header>
        {state === 'loading' ? (
          <div className="space-y-3">
            <Skeleton className="h-5 w-40" label="Loading city" />
            <Skeleton className="h-10 w-72" label="Loading city" />
          </div>
        ) : (
          <>
            <p className="text-sm font-bold uppercase tracking-[0.18em] text-ochre">City guide</p>
            <h1 className="mt-2 font-display text-4xl font-bold leading-tight text-maroon sm:text-5xl">
              {cityName}
            </h1>
            {view && (view.district || view.region) ? (
              <p className="mt-3 text-lg text-ink/70">
                {[view.district, view.region].filter(Boolean).join(' · ')}
              </p>
            ) : null}
            {view && view.destination_count > 0 ? (
              <p className="mt-1 text-sm font-semibold text-teal">
                {view.destination_count} {view.destination_count === 1 ? 'place' : 'places'} to
                explore
              </p>
            ) : null}
          </>
        )}
      </header>

      {/* A single async surface for the whole grouped view. When ready and the
          city has sections we render each group; when ready and empty we show
          the discovery empty state (city with no catalogued records). */}
      <CatalogSection
        emptyActionLabel="Search destinations"
        emptyDescription="We have no catalogued places for this city yet. Search to keep discovering Tamil Nadu."
        headingId="city-sections"
        isEmpty={!hasSections}
        onEmptyAction={goToSearch}
        onRetry={retry}
        state={state}
        title={`Explore ${cityName}`}
      >
        <div className="space-y-12">
          {sections.map((section) => {
            const headingId = `city-section-${section.key}`;
            return (
              <section aria-labelledby={headingId} key={section.key}>
                <SectionHeader headingId={headingId} title={section.title} />
                <DestinationGrid destinations={section.destinations} />
              </section>
            );
          })}
        </div>
      </CatalogSection>
    </div>
  );
}
