import { FormEvent, useState } from 'react';

import { RatingStars } from '../ui/RatingStars';
import { ErrorState } from '../ui/ErrorState';
import { Skeleton } from '../ui/Skeleton';
import { useCreateReview, useReviews } from '../../hooks/useReviews';

const RATINGS = [5, 4, 3, 2, 1] as const;

function formatReviewDate(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? 'Date unavailable'
    : new Intl.DateTimeFormat('en-IN', { dateStyle: 'medium' }).format(date);
}

export function ReviewPanel({ destinationId }: { destinationId: string }) {
  const reviewsQuery = useReviews(destinationId);
  const createReview = useCreateReview(destinationId);
  const [rating, setRating] = useState<number>(5);
  const [text, setText] = useState('');

  if (reviewsQuery.isPending) {
    return <Skeleton className="h-56 w-full" label="Loading traveler reviews" />;
  }

  if (reviewsQuery.isError) {
    return (
      <ErrorState
        message="We could not load traveler reviews. Please try again."
        onRetry={() => {
          void reviewsQuery.refetch();
        }}
        title="Reviews are unavailable"
      />
    );
  }

  const reviews = reviewsQuery.data;
  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    createReview.mutate(
      { rating, ...(text.trim() ? { text: text.trim() } : {}) },
      {
        onSuccess: () => setText(''),
      },
    );
  };

  return (
    <div className="space-y-7">
      <div className="grid gap-6 rounded-2xl border border-gold/25 bg-white p-5 sm:grid-cols-[auto_1fr] sm:items-center">
        <div className="text-center sm:border-r sm:border-gold/20 sm:pr-6">
          <p className="font-display text-4xl font-bold text-maroon">
            {reviews.average_rating?.toFixed(1) ?? '—'}
          </p>
          <RatingStars rating={reviews.average_rating} />
          <p className="mt-1 text-sm text-ink/65">
            {reviews.review_count} {reviews.review_count === 1 ? 'review' : 'reviews'}
          </p>
        </div>
        <dl className="space-y-2" aria-label="Rating distribution">
          {RATINGS.map((value) => {
            const count = reviews.rating_distribution[value] ?? 0;
            const percent = reviews.review_count === 0 ? 0 : (count / reviews.review_count) * 100;
            return (
              <div
                className="grid grid-cols-[3rem_1fr_2rem] items-center gap-2 text-sm"
                key={value}
              >
                <dt>{value} star</dt>
                <dd className="h-2 overflow-hidden rounded-full bg-warm/70">
                  <span
                    aria-hidden="true"
                    className="block h-full rounded-full bg-ochre"
                    style={{ width: `${percent}%` }}
                  />
                  <span className="sr-only">{count} reviews</span>
                </dd>
                <span className="text-right text-ink/65">{count}</span>
              </div>
            );
          })}
        </dl>
      </div>

      {reviews.ai_summary ? (
        <section
          aria-labelledby="ai-review-summary"
          className="rounded-2xl border border-teal/30 bg-teal/5 p-5"
        >
          <div className="flex items-center gap-2">
            <span className="rounded-full bg-teal px-3 py-1 text-xs font-bold uppercase tracking-wide text-white">
              AI summary
            </span>
            <h3 className="font-display text-xl font-bold text-maroon" id="ai-review-summary">
              Visitor feedback themes
            </h3>
          </div>
          <p className="mt-2 text-sm text-ink/70">
            Generated only from {reviews.ai_summary.review_count} traveler reviews.
          </p>
          <div className="mt-3 grid gap-4 sm:grid-cols-2">
            <div>
              <h4 className="font-semibold text-maroon">Highlights</h4>
              <ul className="mt-1 list-disc pl-5 text-sm text-ink/80">
                {reviews.ai_summary.positives.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
            <div>
              <h4 className="font-semibold text-maroon">Considerations</h4>
              <ul className="mt-1 list-disc pl-5 text-sm text-ink/80">
                {reviews.ai_summary.concerns.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
          </div>
        </section>
      ) : null}

      <form className="rounded-2xl border border-teal/30 bg-teal/5 p-5" onSubmit={handleSubmit}>
        <fieldset disabled={createReview.isPending}>
          <legend className="font-display text-xl font-bold text-maroon">
            Share your experience
          </legend>
          <div className="mt-4 flex flex-wrap gap-2" role="radiogroup" aria-label="Your rating">
            {RATINGS.map((value) => (
              <label className="cursor-pointer" key={value}>
                <input
                  checked={rating === value}
                  className="peer sr-only"
                  name="rating"
                  onChange={() => setRating(value)}
                  type="radio"
                  value={value}
                />
                <span className="block rounded-full border border-maroon/30 px-3 py-1.5 text-sm font-semibold text-maroon peer-checked:border-maroon peer-checked:bg-maroon peer-checked:text-white peer-focus-visible:outline peer-focus-visible:outline-2 peer-focus-visible:outline-offset-2 peer-focus-visible:outline-teal">
                  {value} ★
                </span>
              </label>
            ))}
          </div>
          <label className="mt-4 block text-sm font-semibold text-ink" htmlFor="review-text">
            Review <span className="font-normal text-ink/60">(optional)</span>
          </label>
          <textarea
            className="mt-1 min-h-24 w-full rounded-xl border border-gold/35 bg-white p-3 text-ink outline-none focus:border-teal focus:ring-2 focus:ring-teal/30"
            id="review-text"
            maxLength={2000}
            onChange={(event) => setText(event.target.value)}
            value={text}
          />
          {createReview.isError ? (
            <p className="mt-3 text-sm font-medium text-maroon" role="alert">
              We could not submit your review. Check your rating and try again.
            </p>
          ) : null}
          <button
            className="mt-4 rounded-full bg-maroon px-5 py-2.5 font-semibold text-white transition hover:bg-maroon/90 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal disabled:cursor-not-allowed disabled:opacity-60"
            type="submit"
          >
            {createReview.isPending ? 'Submitting review…' : 'Submit review'}
          </button>
        </fieldset>
      </form>

      <section aria-labelledby="recent-reviews-heading">
        <h3 className="font-display text-xl font-bold text-maroon" id="recent-reviews-heading">
          Recent reviews
        </h3>
        {reviews.reviews.length === 0 ? (
          <p className="mt-3 rounded-xl bg-warm/45 p-4 text-ink/70">
            Be the first to share an experience.
          </p>
        ) : (
          <ul className="mt-4 space-y-4">
            {reviews.reviews.map((review) => (
              <li className="rounded-xl border border-gold/20 bg-white p-4" key={review.id}>
                <RatingStars rating={review.rating} />
                {review.text ? <p className="mt-2 text-ink/85">{review.text}</p> : null}
                <p className="mt-2 text-xs text-ink/60">{formatReviewDate(review.created_at)}</p>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
