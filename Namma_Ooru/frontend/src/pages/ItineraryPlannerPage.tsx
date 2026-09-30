import { useState, type FormEvent } from 'react';
import { useMutation } from '@tanstack/react-query';

import { createItinerary, editItinerary } from '../api/client';
import type { Itinerary } from '../api/types';
import { EmptyState } from '../components/ui/EmptyState';
import { ErrorState } from '../components/ui/ErrorState';
import { Skeleton } from '../components/ui/Skeleton';

function formatTime(minutes: number): string {
  const hours = Math.floor(minutes / 60)
    .toString()
    .padStart(2, '0');
  const remaining = (minutes % 60).toString().padStart(2, '0');
  return `${hours}:${remaining}`;
}

function Timeline({ itinerary }: { itinerary: Itinerary }) {
  return (
    <section aria-labelledby="itinerary-timeline" className="space-y-6">
      <div className="flex items-center gap-3">
        <h2 className="font-display text-3xl font-bold text-maroon" id="itinerary-timeline">
          Your day-by-day journey
        </h2>
        <span className="rounded-full bg-ochre/15 px-3 py-1 text-xs font-bold uppercase tracking-wide text-maroon">
          AI itinerary
        </span>
      </div>
      {itinerary.days.map((day) => (
        <article
          className="rounded-2xl border border-gold/30 bg-white/75 p-5 shadow-sm"
          key={day.day_number}
        >
          <h3 className="font-display text-2xl font-bold text-maroon">Day {day.day_number}</h3>
          {day.activities.length === 0 ? (
            <p className="mt-3 text-ink/70">Keep this day open for a slower local discovery.</p>
          ) : (
            <ol className="mt-5 space-y-4 border-l-2 border-teal/35 pl-5">
              {day.activities.map((activity) => (
                <li className="relative" key={`${day.day_number}-${activity.destination_id}`}>
                  <span className="absolute -left-[31px] top-1.5 h-3 w-3 rounded-full bg-teal" />
                  <p className="text-sm font-bold text-teal">
                    {formatTime(activity.start_minute)} · about {activity.duration_minutes} minutes
                  </p>
                  <p className="text-lg font-bold text-maroon">
                    {activity.destination_id.replaceAll('-', ' ')}
                  </p>
                  <p className="mt-1 text-sm text-ink/75">
                    {activity.rationale || 'Selected for this journey.'}
                  </p>
                  <p className="mt-1 text-sm text-ink/70">
                    <strong>Travel context:</strong>{' '}
                    {activity.travel_context || 'Allow time between stops.'}
                  </p>
                  <p className="text-sm text-ink/70">
                    <strong>Break:</strong>{' '}
                    {activity.break_suggestion || 'Pause for a local refreshment.'}
                  </p>
                </li>
              ))}
            </ol>
          )}
        </article>
      ))}
    </section>
  );
}

export function ItineraryPlannerPage() {
  const [context, setContext] = useState('3-day Madurai trip focused on temples, history and food');
  const [days, setDays] = useState(3);
  const [editRequest, setEditRequest] = useState('');
  const [itinerary, setItinerary] = useState<Itinerary | null>(null);
  const [editMessage, setEditMessage] = useState<string | null>(null);

  const createMutation = useMutation({
    mutationFn: createItinerary,
    onSuccess: (plan) => {
      setItinerary(plan);
      setEditMessage(null);
    },
  });
  const editMutation = useMutation({
    mutationFn: ({ id, request }: { id: string; request: string }) => editItinerary(id, request),
    onSuccess: (result) => {
      setItinerary(result.itinerary);
      setEditMessage(result.explanation);
      setEditRequest('');
    },
  });

  const submitPlan = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    createMutation.mutate({
      destination_context: context,
      day_count: days,
      allow_repeats: false,
      constraints: { interests: [], travel_style: null, budget: null, starting_point: null },
    });
  };
  const submitEdit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (itinerary && editRequest.trim())
      editMutation.mutate({ id: itinerary.id, request: editRequest });
  };

  return (
    <div className="space-y-10">
      <header className="max-w-3xl">
        <p className="text-sm font-bold uppercase tracking-[0.18em] text-ochre">Travel studio</p>
        <h1 className="mt-2 font-display text-4xl font-bold text-maroon sm:text-5xl">
          Plan your Tamil Nadu journey
        </h1>
        <p className="mt-3 text-lg text-ink/75">
          Choose your trip shape, then refine the itinerary in conversation.
        </p>
      </header>
      <form
        className="grid gap-4 rounded-2xl bg-maroon p-6 text-sand shadow-lg sm:grid-cols-[1fr_8rem_auto]"
        onSubmit={submitPlan}
      >
        <label className="font-semibold">
          Trip focus
          <input
            className="mt-2 w-full rounded-lg border-0 px-3 py-3 text-ink"
            value={context}
            onChange={(event) => setContext(event.target.value)}
          />
        </label>
        <label className="font-semibold">
          Days
          <input
            className="mt-2 w-full rounded-lg border-0 px-3 py-3 text-ink"
            min="1"
            max="14"
            type="number"
            value={days}
            onChange={(event) => setDays(Number(event.target.value))}
          />
        </label>
        <button
          className="self-end rounded-full bg-gold px-5 py-3 font-bold text-maroon hover:bg-sand disabled:opacity-60"
          disabled={createMutation.isPending}
          type="submit"
        >
          {createMutation.isPending ? 'Planning…' : 'Create itinerary'}
        </button>
      </form>
      {createMutation.isPending ? <Skeleton className="h-96" label="Generating itinerary" /> : null}
      {createMutation.isError ? (
        <ErrorState
          message="We could not generate this itinerary. Please try again."
          onRetry={() => createMutation.reset()}
        />
      ) : null}
      {!itinerary && !createMutation.isPending && !createMutation.isError ? (
        <EmptyState
          description="Start with a destination and trip length to see a practical day-by-day route."
          title="Your itinerary will appear here"
        />
      ) : null}
      {itinerary ? (
        <>
          <Timeline itinerary={itinerary} />
          <section
            className="rounded-2xl border border-teal/25 bg-teal/5 p-6"
            aria-labelledby="edit-itinerary"
          >
            <h2 className="font-display text-2xl font-bold text-maroon" id="edit-itinerary">
              Refine with a conversational edit
            </h2>
            <p className="mt-1 text-sm text-ink/75">
              Try “remove madurai-temple”, “add madurai-museum”, or “replace old-place with
              new-place”.
            </p>
            <form className="mt-4 flex flex-col gap-3 sm:flex-row" onSubmit={submitEdit}>
              <label className="sr-only" htmlFor="itinerary-edit">
                Itinerary edit request
              </label>
              <input
                className="min-w-0 flex-1 rounded-lg border border-teal/35 px-3 py-3"
                id="itinerary-edit"
                value={editRequest}
                onChange={(event) => setEditRequest(event.target.value)}
                placeholder="How would you like to change the trip?"
              />
              <button
                className="rounded-full bg-teal px-5 py-3 font-bold text-white disabled:opacity-60"
                disabled={editMutation.isPending || !editRequest.trim()}
                type="submit"
              >
                {editMutation.isPending ? 'Updating…' : 'Update plan'}
              </button>
            </form>
            {editMessage ? (
              <p className="mt-3 text-sm text-ink/80" role="status">
                {editMessage}
              </p>
            ) : null}
            {editMutation.isError ? (
              <p className="mt-3 text-sm font-semibold text-maroon" role="alert">
                We could not apply that edit. Please try again.
              </p>
            ) : null}
          </section>
        </>
      ) : null}
    </div>
  );
}
