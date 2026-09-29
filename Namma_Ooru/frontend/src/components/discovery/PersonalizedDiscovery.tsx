/**
 * Personalized discovery orchestrator (Requirements 8.1, 8.2, 8.3). It lets a
 * traveler discover destinations three ways, all driven by `POST
 * /api/recommendations` via React Query (no hard-coded destinations):
 *
 * - Interests (8.1): toggle interests to see matching destinations.
 * - Themed journeys (8.3): pick one of the eight named journeys.
 * - Surprise Me / Beyond the Tourist Map (8.2): reveal a single lesser-known pick
 *   with its source facts and a clearly badged AI rationale.
 *
 * Results render through `CatalogSection`, so every data-driven view shows exactly
 * one of content, skeleton (loading), empty, or error (UI steering). All shaping
 * is delegated to `lib/recommendations`; this component stays presentational plus
 * local selection state.
 */

import { useMemo, useState } from 'react';

import type { RecommendationRequest, ThemedJourney } from '../../api/types';
import { useRecommendations } from '../../hooks/useRecommendations';
import { journeyLabel, toggleInterest } from '../../lib/recommendations';
import { CatalogSection } from '../catalog/CatalogSection';
import { DestinationGrid } from '../catalog/DestinationGrid';
import { InterestPicker } from './InterestPicker';
import { JourneyPicker } from './JourneyPicker';
import { SurprisePick } from './SurprisePick';

type DiscoveryTab = 'interests' | 'journey' | 'surprise';

const TABS: readonly { id: DiscoveryTab; label: string }[] = [
  { id: 'interests', label: 'By interest' },
  { id: 'journey', label: 'Themed journeys' },
  { id: 'surprise', label: 'Surprise me' },
];

/** Build the active recommendation request from the current selection, or `null`
 * to keep the query disabled until the traveler has made a usable choice. */
function toRequest(
  tab: DiscoveryTab,
  interests: readonly string[],
  journey: ThemedJourney | null,
  surpriseSeed: number | null,
): RecommendationRequest | null {
  if (tab === 'interests') {
    return interests.length > 0 ? { mode: 'interests', interests: [...interests] } : null;
  }
  if (tab === 'journey') {
    return journey ? { mode: 'journey', journey } : null;
  }
  return surpriseSeed !== null ? { mode: 'surprise', seed: surpriseSeed } : null;
}

export function PersonalizedDiscovery() {
  const [tab, setTab] = useState<DiscoveryTab>('interests');
  const [interests, setInterests] = useState<string[]>([]);
  const [journey, setJourney] = useState<ThemedJourney | null>(null);
  const [surpriseSeed, setSurpriseSeed] = useState<number | null>(null);

  const request = useMemo(
    () => toRequest(tab, interests, journey, surpriseSeed),
    [tab, interests, journey, surpriseSeed],
  );
  const query = useRecommendations(request);

  const toggleInterestValue = (interest: string) => {
    setInterests((current) => toggleInterest(current, interest));
  };

  const rollSurprise = () => {
    // A fresh seed re-rolls the pick via a new query key.
    setSurpriseSeed(Math.floor(Math.random() * 1_000_001));
  };

  const retry = () => {
    void query.refetch();
  };

  // No selection yet ⇒ prompt rather than fetch; a made selection ⇒ reflect the
  // React Query state so the section renders skeleton/empty/error/content.
  const state: 'loading' | 'error' | 'ready' =
    request === null ? 'ready' : query.isPending ? 'loading' : query.isError ? 'error' : 'ready';

  const result = query.data ?? null;
  const destinations = result?.destinations ?? [];
  const surprise = result?.surprise ?? null;

  const heading =
    tab === 'journey' && journey
      ? `${journeyLabel(journey)} picks`
      : tab === 'surprise'
        ? 'Your surprise pick'
        : 'Matched to your interests';

  const emptyDescription =
    request === null
      ? tab === 'interests'
        ? 'Choose one or more interests above to see matching destinations.'
        : tab === 'journey'
          ? 'Choose a themed journey above to see matching destinations.'
          : 'Tap Surprise me to reveal a lesser-known place beyond the tourist map.'
      : 'No destinations matched this selection yet. Try another interest or journey.';

  const isEmpty =
    request === null || (tab === 'surprise' ? surprise === null : destinations.length === 0);

  return (
    <section aria-labelledby="section-discovery" className="mt-12">
      <div className="mb-5">
        <p className="text-xs font-bold uppercase tracking-[0.18em] text-ochre">
          Beyond the tourist map
        </p>
        <h2
          className="font-display text-2xl font-bold text-maroon sm:text-3xl"
          id="section-discovery"
        >
          Discover your way
        </h2>
        <p className="mt-1 max-w-2xl text-ink/70">
          Personalized recommendations across every district — pick your interests, follow a themed
          journey, or let us surprise you.
        </p>
      </div>

      <div
        aria-label="Discovery mode"
        className="mb-5 inline-flex flex-wrap gap-2 rounded-full border border-gold/30 bg-white p-1"
        role="tablist"
      >
        {TABS.map((entry) => {
          const isActive = tab === entry.id;
          return (
            <button
              aria-selected={isActive}
              className={`rounded-full px-4 py-2 text-sm font-semibold transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ochre ${
                isActive ? 'bg-maroon text-sand' : 'text-maroon hover:bg-ochre/10'
              }`}
              id={`discovery-tab-${entry.id}`}
              key={entry.id}
              onClick={() => setTab(entry.id)}
              role="tab"
              type="button"
            >
              {entry.label}
            </button>
          );
        })}
      </div>

      <div className="mb-6">
        {tab === 'interests' ? (
          <InterestPicker onToggle={toggleInterestValue} selected={interests} />
        ) : null}
        {tab === 'journey' ? <JourneyPicker onSelect={setJourney} selected={journey} /> : null}
        {tab === 'surprise' ? (
          <button
            className="rounded-full bg-teal px-6 py-3 font-semibold text-white transition hover:bg-teal/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ochre"
            onClick={rollSurprise}
            type="button"
          >
            {surpriseSeed === null ? 'Surprise me' : 'Surprise me again'}
          </button>
        ) : null}
      </div>

      <CatalogSection
        emptyDescription={emptyDescription}
        headingId="section-discovery-results"
        isEmpty={isEmpty}
        onRetry={retry}
        skeletonCount={tab === 'surprise' ? 1 : 4}
        state={state}
        title={heading}
      >
        {tab === 'surprise' && surprise ? (
          <SurprisePick headingId="surprise-rationale" surprise={surprise} />
        ) : (
          <DestinationGrid destinations={destinations} />
        )}
      </CatalogSection>
    </section>
  );
}
