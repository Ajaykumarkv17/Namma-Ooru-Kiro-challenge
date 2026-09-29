/**
 * A single Surprise Me pick (Requirement 8.2 + the "beyond the famous" discovery
 * principle). The source catalog facts — the destination card, its category,
 * suggested duration, and short description — are rendered plainly, while the
 * AI-generated `rationale` is visually badged "AI pick" and kept in a separate,
 * clearly labelled block so generated prose is never conflated with source facts
 * (UI + AI/RAG steering). Selecting the card navigates to the destination detail.
 */

import type { SurpriseRecommendation } from '../../api/types';
import { CATEGORY_LABELS } from '../../lib/catalog';
import { formatSuggestedDuration } from '../../lib/recommendations';
import { DestinationCard } from '../catalog/DestinationCard';

type SurprisePickProps = {
  surprise: SurpriseRecommendation;
  headingId: string;
};

export function SurprisePick({ surprise, headingId }: SurprisePickProps) {
  const { destination, category, suggested_duration_minutes, short_description, rationale } =
    surprise;
  const duration = formatSuggestedDuration(suggested_duration_minutes);
  const categoryLabel = CATEGORY_LABELS[category];

  return (
    <div className="grid grid-cols-1 gap-5 lg:grid-cols-[minmax(0,20rem)_1fr]">
      {/* Source facts: the catalogued destination and its verified details. */}
      <div>
        <DestinationCard destination={destination} />
      </div>

      <div className="flex flex-col gap-4">
        <dl className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <div className="rounded-2xl border border-gold/25 bg-white p-4">
            <dt className="text-xs font-bold uppercase tracking-wide text-ink/60">Category</dt>
            <dd className="mt-1 font-semibold text-maroon">{categoryLabel}</dd>
          </div>
          <div className="rounded-2xl border border-gold/25 bg-white p-4">
            <dt className="text-xs font-bold uppercase tracking-wide text-ink/60">
              Suggested time
            </dt>
            <dd className="mt-1 font-semibold text-maroon">
              {duration ?? <span className="text-ink/60">Information unavailable</span>}
            </dd>
          </div>
          <div className="rounded-2xl border border-gold/25 bg-white p-4 sm:col-span-2">
            <dt className="text-xs font-bold uppercase tracking-wide text-ink/60">
              Why it stands out
            </dt>
            <dd className="mt-1 text-ink/80">{short_description}</dd>
          </div>
        </dl>

        {/* AI-generated rationale, badged and separated from the source facts. */}
        <section
          aria-labelledby={headingId}
          className="rounded-2xl border border-teal/30 bg-teal/5 p-4"
        >
          <div className="flex items-center gap-2">
            <span className="rounded-full bg-teal px-2.5 py-0.5 text-xs font-bold uppercase tracking-wide text-white">
              AI pick
            </span>
            <h3 className="text-sm font-semibold text-teal" id={headingId}>
              Why we chose this for you
            </h3>
          </div>
          <p className="mt-2 text-ink/80">{rationale}</p>
        </section>
      </div>
    </div>
  );
}
