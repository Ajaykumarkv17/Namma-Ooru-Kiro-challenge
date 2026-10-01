import { useState, type FormEvent } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Link } from 'react-router-dom';

import { askChat } from '../../api/client';
import { ErrorState } from '../ui/ErrorState';
import { Skeleton } from '../ui/Skeleton';

export function ChatWidget() {
  const [question, setQuestion] = useState('');
  const chat = useMutation({ mutationFn: askChat });

  function submitQuestion(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (question.trim()) {
      chat.mutate({ question: question.trim() });
    }
  }

  return (
    <section
      aria-labelledby="travel-assistant-heading"
      className="rounded-2xl border border-teal/30 bg-teal/5 p-5 shadow-sm"
    >
      <div className="flex flex-wrap items-center gap-2">
        <span className="rounded-full bg-teal px-3 py-1 text-xs font-bold uppercase tracking-wide text-white">
          AI assistant
        </span>
        <h2 className="font-display text-xl font-bold text-maroon" id="travel-assistant-heading">
          Ask Namma Ooru
        </h2>
      </div>
      <p className="mt-2 text-sm text-ink/75">
        Ask about the sourced travel data. Answers cite the destination records returned by the
        service.
      </p>
      <form className="mt-4 flex flex-col gap-3 sm:flex-row" onSubmit={submitQuestion}>
        <label className="sr-only" htmlFor="chat-question">
          Travel question
        </label>
        <input
          className="min-w-0 flex-1 rounded-xl border border-teal/35 bg-white px-3 py-3 text-ink outline-none focus:border-teal focus:ring-2 focus:ring-teal/30"
          id="chat-question"
          onChange={(event) => setQuestion(event.target.value)}
          placeholder="Ask about a place, culture, or trip idea"
          value={question}
        />
        <button
          className="rounded-full bg-maroon px-5 py-3 font-semibold text-white hover:bg-maroon/90 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal disabled:opacity-60"
          disabled={!question.trim() || chat.isPending}
          type="submit"
        >
          {chat.isPending ? 'Finding sources…' : 'Ask'}
        </button>
      </form>
      {chat.isPending ? (
        <Skeleton className="mt-4 h-24 w-full" label="Finding a grounded answer" />
      ) : null}
      {chat.isError ? (
        <div className="mt-4">
          <ErrorState
            message="We could not answer that question right now. Please try again."
            onRetry={() => chat.reset()}
            title="Travel assistant unavailable"
          />
        </div>
      ) : null}
      {chat.data ? (
        <div aria-live="polite" className="mt-4 rounded-xl border border-gold/25 bg-white p-4">
          <p className="text-xs font-bold uppercase tracking-wide text-teal">
            AI-generated response
          </p>
          <p className="mt-2 text-ink/85">{chat.data.answer}</p>
          {chat.data.sources.length > 0 ? (
            <div className="mt-4 border-t border-gold/20 pt-3">
              <h3 className="text-sm font-bold text-maroon">Source destinations</h3>
              <ul className="mt-2 space-y-1">
                {chat.data.sources.map((source) => (
                  <li className="text-sm" key={`${source.destination_id}-${source.url}`}>
                    <Link
                      className="font-semibold text-teal underline underline-offset-2"
                      to={`/destinations/${source.destination_id}`}
                    >
                      {source.name}
                    </Link>{' '}
                    <a
                      className="text-ink/70 underline underline-offset-2"
                      href={source.url}
                      rel="noreferrer"
                      target="_blank"
                    >
                      Source link
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}
