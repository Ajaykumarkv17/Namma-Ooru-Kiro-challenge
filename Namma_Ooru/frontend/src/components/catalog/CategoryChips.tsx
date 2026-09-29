/**
 * Category chips linking into filtered search. Each chip navigates to
 * `/search?category=<slug>` so travelers can browse by interest without AI.
 */

import { Link } from 'react-router-dom';

import type { CategorySummary } from '../../lib/catalog';

type CategoryChipsProps = {
  categories: readonly CategorySummary[];
};

export function CategoryChips({ categories }: CategoryChipsProps) {
  return (
    <ul className="flex flex-wrap gap-3">
      {categories.map((entry) => (
        <li key={entry.category}>
          <Link
            className="inline-flex items-center gap-2 rounded-full border border-gold/40 bg-white px-4 py-2 font-semibold text-maroon transition hover:border-ochre hover:bg-ochre/10 focus-visible:border-ochre"
            to={`/search?category=${entry.category}`}
          >
            {entry.label}
            <span aria-hidden="true" className="text-sm font-normal text-ink/60">
              {entry.destinationCount}
            </span>
          </Link>
        </li>
      ))}
    </ul>
  );
}
