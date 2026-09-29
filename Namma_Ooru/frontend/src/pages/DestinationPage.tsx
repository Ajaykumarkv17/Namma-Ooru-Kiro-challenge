/**
 * Destination detail page (Requirements 2.2, 2.3, 2.4). Displays the description,
 * category, image, ratings, a reviews placeholder area, best time to visit,
 * recommended duration, source links, and nearby places. Nullable factual fields
 * render "Information unavailable" via `InfoField` rather than a fabricated value
 * (Requirement 2.3). Selecting a nearby place navigates to that Destination
 * (Requirement 2.4). Data comes from `GET /api/destinations/{id}` via React Query.
 */

import { useParams } from 'react-router-dom';

import type { Destination } from '../api/types';
import { DestinationGrid } from '../components/catalog/DestinationGrid';
import { ErrorState } from '../components/ui/ErrorState';
import { InfoField } from '../components/ui/InfoField';
import { RatingStars } from '../components/ui/RatingStars';
import { SectionHeader } from '../components/ui/SectionHeader';
import { Skeleton } from '../components/ui/Skeleton';
import { useDestination } from '../hooks/useDestinations';
import { CATEGORY_LABELS } from '../lib/catalog';

/** Human-readable recommended duration, or null when unverified. */
function formatDuration(minutes: number | null): string | null {
  if (minutes === null) {
    return null;
  }
  if (minutes < 60) {
    return `${minutes} min`;
  }
  const hours = Math.floor(minutes / 60);
  const remainder = minutes % 60;
  const hourLabel = `${hours} ${hours === 1 ? 'hour' : 'hours'}`;
  return remainder === 0 ? hourLabel : `${hourLabel} ${remainder} min`;
}

/** Short, human-readable label for a source host, falling back to the raw URL. */
function sourceLabel(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, '');
  } catch {
    return url;
  }
}

function DestinationContent({
  destination,
  nearby,
}: {
  destination: Destination;
  nearby: readonly Destination[];
}) {
  const categoryLabel = CATEGORY_LABELS[destination.category];
  const duration = formatDuration(destination.recommended_duration_minutes);
  const detailId = 'destination-detail';

  return (
    <article aria-labelledby={detailId} className="space-y-10">
      <header>
        <p className="text-sm font-bold uppercase tracking-[0.18em] text-ochre">{categoryLabel}</p>
        <h1
          className="mt-2 font-display text-4xl font-bold leading-tight text-maroon sm:text-5xl"
          id={detailId}
        >
          {destination.name}
        </h1>
        <p className="mt-3 text-lg text-ink/70">
          {destination.city}, {destination.district} · {destination.region}
        </p>
        <div className="mt-3">
          <RatingStars
            count={destination.popularity.rating_count}
            rating={destination.popularity.rating_average}
          />
        </div>
      </header>

      <div className="overflow-hidden rounded-3xl border border-gold/25 bg-ochre/10">
        {destination.image_reference ? (
          <img
            alt={`${destination.name}, ${categoryLabel} in ${destination.city}`}
            className="aspect-[16/9] w-full object-cover"
            src={destination.image_reference}
          />
        ) : (
          <div
            aria-hidden="true"
            className="flex aspect-[16/9] w-full items-center justify-center bg-gradient-to-br from-ochre/25 to-maroon/20 font-display text-6xl text-maroon/70"
          >
            {destination.name.charAt(0)}
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 gap-10 lg:grid-cols-3">
        <div className="space-y-8 lg:col-span-2">
          <section aria-labelledby="about-heading">
            <SectionHeader headingId="about-heading" title="About this place" />
            <p className="text-ink/85">{destination.description}</p>
            {destination.detailed_description ? (
              <p className="mt-4 text-ink/85">{destination.detailed_description}</p>
            ) : null}
          </section>

          <section aria-labelledby="history-heading">
            <SectionHeader headingId="history-heading" title="History & culture" />
            <dl className="grid grid-cols-1 gap-5 sm:grid-cols-2">
              <InfoField
                label="Historical significance"
                value={destination.historical_significance}
              />
              <InfoField label="Cultural significance" value={destination.cultural_significance} />
            </dl>
          </section>

          {/* AI summary area, clearly badged and separated from source content.
              Wiring of the generated summary arrives in task 8.4; until then we
              show a labelled placeholder and never fabricate content. */}
          <section aria-labelledby="ai-summary-heading">
            <div className="rounded-2xl border border-teal/40 bg-teal/5 p-5">
              <div className="mb-2 flex items-center gap-2">
                <span className="rounded-full bg-teal px-3 py-1 text-xs font-semibold text-white">
                  AI summary
                </span>
                <h2 className="font-display text-lg font-bold text-maroon" id="ai-summary-heading">
                  Grounded overview
                </h2>
              </div>
              <p className="text-ink/70">
                An AI-generated, source-grounded summary will appear here. It is kept separate from
                the source-verified details above.
              </p>
            </div>
          </section>

          {/* Reviews placeholder. The review panel arrives in task 7.3; this
              labelled area keeps the page structure without inventing reviews. */}
          <section aria-labelledby="reviews-heading">
            <SectionHeader headingId="reviews-heading" title="Reviews" />
            <div className="rounded-2xl border border-gold/25 bg-white p-5 text-ink/70">
              Traveler reviews will appear here.
            </div>
          </section>
        </div>

        <aside aria-labelledby="visit-heading" className="space-y-4">
          <h2 className="font-display text-xl font-bold text-maroon" id="visit-heading">
            Plan your visit
          </h2>
          <dl className="space-y-4 rounded-2xl border border-gold/25 bg-white p-5">
            <InfoField label="Best time to visit" value={destination.best_time_to_visit} />
            <InfoField label="Recommended duration" value={duration} />
            <InfoField label="Opening hours" value={destination.opening_hours} />
            <InfoField label="Entry fee" value={destination.entry_fee} />
            <InfoField label="Address" value={destination.address} />
            <InfoField
              label="Official website"
              render={(value) => (
                <a
                  className="text-teal underline decoration-teal/40 underline-offset-2 hover:decoration-teal"
                  href={value}
                  rel="noreferrer"
                  target="_blank"
                >
                  {sourceLabel(value)}
                </a>
              )}
              value={destination.official_website}
            />
          </dl>

          <div className="rounded-2xl border border-gold/25 bg-white p-5">
            <h3 className="text-xs font-bold uppercase tracking-[0.14em] text-ochre">Sources</h3>
            {destination.source_urls.length > 0 ? (
              <ul className="mt-2 space-y-1">
                {destination.source_urls.map((url) => (
                  <li key={url}>
                    <a
                      className="text-sm text-teal underline decoration-teal/40 underline-offset-2 hover:decoration-teal"
                      href={url}
                      rel="noreferrer"
                      target="_blank"
                    >
                      {sourceLabel(url)}
                    </a>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mt-2 text-sm italic text-ink/50">Information unavailable</p>
            )}
          </div>
        </aside>
      </div>

      {nearby.length > 0 ? (
        <section aria-labelledby="nearby-heading">
          <SectionHeader
            description="Other places within reach — selecting one opens its details."
            headingId="nearby-heading"
            title="Nearby places"
          />
          <DestinationGrid destinations={nearby} />
        </section>
      ) : null}
    </article>
  );
}

export function DestinationPage() {
  const { destinationId } = useParams<{ destinationId: string }>();
  const query = useDestination(destinationId ?? '');

  if (query.isPending) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-6 w-32" label="Loading destination" />
        <Skeleton className="h-12 w-80" label="Loading destination" />
        <Skeleton className="h-72 w-full" label="Loading destination" />
      </div>
    );
  }

  if (query.isError) {
    return (
      <ErrorState
        message="We could not load this destination. It may not exist, or the connection failed."
        onRetry={() => {
          void query.refetch();
        }}
      />
    );
  }

  return <DestinationContent destination={query.data.destination} nearby={query.data.nearby} />;
}
