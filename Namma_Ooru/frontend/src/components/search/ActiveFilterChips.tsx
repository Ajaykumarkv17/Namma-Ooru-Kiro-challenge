/**
 * Visible chips for the deterministic filters a search resolved to (Requirement
 * 4.2). These are the source-derived constraints applied to the catalog — kept
 * visually distinct from the AI-derived interpretation (AI/RAG steering).
 */

import type { ActiveFilterChip } from '../../lib/search';

type ActiveFilterChipsProps = {
  chips: readonly ActiveFilterChip[];
  headingId: string;
};

export function ActiveFilterChips({ chips, headingId }: ActiveFilterChipsProps) {
  if (chips.length === 0) {
    return null;
  }

  return (
    <section aria-labelledby={headingId} className="mt-4">
      <h2 className="text-xs font-bold uppercase tracking-[0.18em] text-ochre" id={headingId}>
        Active filters
      </h2>
      <ul className="mt-2 flex flex-wrap gap-2">
        {chips.map((chip) => (
          <li key={chip.key}>
            <span className="inline-flex items-center gap-2 rounded-full border border-gold/50 bg-white px-3 py-1.5 text-sm font-semibold text-maroon">
              <span className="text-ink/60">{chip.label}:</span>
              {chip.value}
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}
