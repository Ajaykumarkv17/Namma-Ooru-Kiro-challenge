/**
 * Home hero: the discovery entry point. Presents the tagline, a destination
 * search control, and an "Explore Tamil Nadu" call to action (Requirement 1.1).
 * Submitting the search navigates to `/search` with the query; it does not
 * require an AI request to browse.
 */

import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';

export function HomeHero() {
  const navigate = useNavigate();
  const [query, setQuery] = useState('');

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = query.trim();
    navigate(trimmed ? `/search?q=${encodeURIComponent(trimmed)}` : '/search');
  }

  return (
    <section className="rounded-3xl bg-maroon px-6 py-14 text-sand shadow-lg sm:px-12 sm:py-16">
      <p className="text-sm font-bold uppercase tracking-[0.18em] text-gold">Tamil Nadu travel</p>
      <h1 className="mt-4 max-w-3xl font-display text-4xl font-bold leading-tight sm:text-6xl">
        Discover the Tamil Nadu you haven’t seen.
      </h1>
      <p className="mt-5 max-w-2xl text-lg leading-8 text-sand/90">
        Explore temples, coastlines, hill towns, and hidden gems across every district — with
        source-attributed details and journeys built around what matters to you.
      </p>

      <form
        aria-label="Search destinations"
        className="mt-8 flex w-full max-w-2xl flex-col gap-3 sm:flex-row"
        onSubmit={handleSubmit}
        role="search"
      >
        <label className="sr-only" htmlFor="home-search">
          Search Tamil Nadu destinations
        </label>
        <input
          autoComplete="off"
          className="w-full rounded-full border border-transparent bg-sand px-5 py-3 text-ink placeholder:text-ink/50 focus:border-gold focus-visible:outline-none"
          id="home-search"
          name="q"
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Try “temples and food in Madurai”"
          type="search"
          value={query}
        />
        <button
          className="rounded-full bg-gold px-6 py-3 font-semibold text-maroon transition hover:bg-gold/90"
          type="submit"
        >
          Search
        </button>
      </form>

      <div className="mt-6">
        <a
          className="inline-flex items-center gap-2 rounded-full border border-gold/60 px-6 py-3 font-semibold text-sand transition hover:bg-gold/15"
          href="#explore-tamil-nadu"
        >
          Explore Tamil Nadu
          <span aria-hidden="true">↓</span>
        </a>
      </div>
    </section>
  );
}
