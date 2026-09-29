/**
 * Themed-journey selector (Requirement 8.3). Presentational — it renders the eight
 * named journeys as selectable cards and hands the chosen slug up; the page/hook
 * layer fetches `{ mode: "journey", journey: <slug> }`.
 */

import type { ThemedJourney } from '../../api/types';
import { JOURNEY_OPTIONS } from '../../lib/recommendations';

type JourneyPickerProps = {
  /** The currently selected journey, or `null` when none is chosen. */
  selected: ThemedJourney | null;
  /** Called with a journey slug when the traveler selects it. */
  onSelect: (journey: ThemedJourney) => void;
};

export function JourneyPicker({ selected, onSelect }: JourneyPickerProps) {
  return (
    <ul
      aria-label="Choose a themed journey"
      className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4"
      role="group"
    >
      {JOURNEY_OPTIONS.map((option) => {
        const isSelected = selected === option.slug;
        return (
          <li key={option.slug}>
            <button
              aria-pressed={isSelected}
              className={`flex h-full w-full flex-col gap-1 rounded-2xl border p-4 text-left transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ochre ${
                isSelected
                  ? 'border-maroon bg-maroon/5 shadow-md'
                  : 'border-gold/30 bg-white shadow-sm hover:border-ochre hover:shadow-md'
              }`}
              onClick={() => onSelect(option.slug)}
              type="button"
            >
              <span className="font-display text-lg font-bold text-maroon">{option.label}</span>
              <span className="text-sm text-ink/70">{option.description}</span>
            </button>
          </li>
        );
      })}
    </ul>
  );
}
