/**
 * Accessible star rating. The visual stars are decorative; the rating is conveyed
 * to assistive technology through an accessible label so meaning is not lost
 * (UI/UX steering: icons that convey meaning have labels).
 */

type RatingStarsProps = {
  /** Average rating from 1–5, or null when no rating is available. */
  rating: number | null;
  /** Number of ratings behind the average, shown alongside the stars. */
  count?: number;
};

const MAX_STARS = 5;

export function RatingStars({ rating, count }: RatingStarsProps) {
  if (rating === null) {
    return <p className="text-sm text-ink/60">No ratings yet</p>;
  }

  const rounded = Math.round(rating);
  const label =
    count && count > 0
      ? `Rated ${rating.toFixed(1)} out of 5 from ${count} ${count === 1 ? 'review' : 'reviews'}`
      : `Rated ${rating.toFixed(1)} out of 5`;

  return (
    <p className="flex items-center gap-1.5 text-sm text-ink/80">
      <span aria-hidden="true" className="text-gold">
        {Array.from({ length: MAX_STARS }, (_, index) => (index < rounded ? '★' : '☆')).join('')}
      </span>
      <span className="sr-only">{label}</span>
      <span aria-hidden="true" className="font-semibold">
        {rating.toFixed(1)}
      </span>
      {count && count > 0 ? (
        <span aria-hidden="true" className="text-ink/60">
          ({count})
        </span>
      ) : null}
    </p>
  );
}
