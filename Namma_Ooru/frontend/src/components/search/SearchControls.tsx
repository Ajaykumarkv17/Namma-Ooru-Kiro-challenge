/**
 * Search controls: a labelled Travel Query input and submit button (Requirement
 * 4.2). Presentational — it owns only the input's local text and hands the
 * trimmed query up via `onSubmit`, so the page/hook layer owns the actual search.
 */

import { useEffect, useState, type FormEvent } from 'react';

type SearchControlsProps = {
  /** The query currently reflected in the URL, used to seed the input. */
  initialQuery: string;
  /** Called with the trimmed query when the traveler submits a non-empty query. */
  onSubmit: (query: string) => void;
};

export function SearchControls({ initialQuery, onSubmit }: SearchControlsProps) {
  const [value, setValue] = useState(initialQuery);

  // Keep the input in sync when the query changes via navigation (e.g. the home
  // hero, a category chip, or the browser back button).
  useEffect(() => {
    setValue(initialQuery);
  }, [initialQuery]);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = value.trim();
    if (trimmed.length > 0) {
      onSubmit(trimmed);
    }
  }

  return (
    <form
      aria-label="Search destinations"
      className="flex w-full max-w-2xl flex-col gap-3 sm:flex-row"
      onSubmit={handleSubmit}
      role="search"
    >
      <label className="sr-only" htmlFor="search-query">
        Search Tamil Nadu destinations
      </label>
      <input
        autoComplete="off"
        className="w-full rounded-full border border-gold/40 bg-white px-5 py-3 text-ink placeholder:text-ink/50 focus:border-ochre focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ochre"
        id="search-query"
        maxLength={2000}
        name="q"
        onChange={(event) => setValue(event.target.value)}
        placeholder="Try “temples and food in Madurai”"
        type="search"
        value={value}
      />
      <button
        className="rounded-full bg-maroon px-6 py-3 font-semibold text-sand transition hover:bg-maroon/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ochre"
        type="submit"
      >
        Search
      </button>
    </form>
  );
}
