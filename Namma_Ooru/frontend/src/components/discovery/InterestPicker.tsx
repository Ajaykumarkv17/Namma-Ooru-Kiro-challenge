/**
 * Interest toggles for personalized discovery (Requirement 8.1). Presentational —
 * it renders the curated interest options as accessible toggle buttons and hands
 * selection changes up; the page/hook layer owns the actual recommendation fetch.
 */

import { INTEREST_OPTIONS } from '../../lib/recommendations';

type InterestPickerProps = {
  /** The currently selected interest values. */
  selected: readonly string[];
  /** Called with an interest value when the traveler toggles it. */
  onToggle: (interest: string) => void;
};

export function InterestPicker({ selected, onToggle }: InterestPickerProps) {
  return (
    <div className="rounded-2xl border border-gold/30 bg-white p-4 shadow-sm">
      <p className="text-sm font-semibold text-ink/70">Pick the experiences you love</p>
      <ul className="mt-3 flex flex-wrap gap-2" role="group" aria-label="Choose interests">
        {INTEREST_OPTIONS.map((option) => {
          const isSelected = selected.includes(option.value);
          return (
            <li key={option.value}>
              <button
                aria-pressed={isSelected}
                className={`rounded-full border px-4 py-2 text-sm font-semibold transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ochre ${
                  isSelected
                    ? 'border-maroon bg-maroon text-sand'
                    : 'border-gold/40 bg-white text-maroon hover:border-ochre hover:bg-ochre/10'
                }`}
                onClick={() => onToggle(option.value)}
                type="button"
              >
                {option.label}
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
