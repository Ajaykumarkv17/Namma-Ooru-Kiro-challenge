/**
 * The AI-derived interpretation of the Travel Query (Requirement 4.1), rendered
 * as labelled chips and clearly badged "AI interpretation" so it is never
 * conflated with source catalog data (AI/RAG + UI steering). Renders nothing when
 * the model recognized no intent facets.
 */

import type { IntentChip } from '../../lib/search';

type SearchInterpretationProps = {
  chips: readonly IntentChip[];
  headingId: string;
};

export function SearchInterpretation({ chips, headingId }: SearchInterpretationProps) {
  if (chips.length === 0) {
    return null;
  }

  return (
    <section
      aria-labelledby={headingId}
      className="mt-4 rounded-2xl border border-teal/30 bg-teal/5 p-4"
    >
      <div className="flex items-center gap-2">
        <span className="rounded-full bg-teal px-2.5 py-0.5 text-xs font-bold uppercase tracking-wide text-white">
          AI interpretation
        </span>
        <h2 className="text-sm font-semibold text-teal" id={headingId}>
          How we read your search
        </h2>
      </div>
      <ul className="mt-3 flex flex-wrap gap-2">
        {chips.map((chip) => (
          <li key={chip.key}>
            <span className="inline-flex items-center gap-2 rounded-full border border-teal/40 bg-white px-3 py-1.5 text-sm font-semibold text-teal">
              <span className="text-ink/60">{chip.label}:</span>
              {chip.value}
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}
