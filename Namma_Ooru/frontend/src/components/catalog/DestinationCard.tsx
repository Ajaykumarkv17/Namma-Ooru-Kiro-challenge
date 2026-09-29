/**
 * A destination card that links to its detail page. Selecting the card navigates
 * to `/destinations/:id` with no AI request (Requirement 1.5). Presentational
 * only — it receives a fully shaped `Destination` from the data layer.
 */

import { Link } from 'react-router-dom';

import type { Destination } from '../../api/types';
import { CATEGORY_LABELS } from '../../lib/catalog';
import { RatingStars } from '../ui/RatingStars';

type DestinationCardProps = {
  destination: Destination;
};

export function DestinationCard({ destination }: DestinationCardProps) {
  const {
    id,
    name,
    city,
    district,
    category,
    description,
    image_reference: imageReference,
    is_hidden_gem: isHiddenGem,
    popularity,
  } = destination;

  const categoryLabel = CATEGORY_LABELS[category];

  return (
    <Link
      className="group flex h-full flex-col overflow-hidden rounded-2xl border border-gold/25 bg-white shadow-sm transition hover:-translate-y-0.5 hover:shadow-md focus-visible:-translate-y-0.5 focus-visible:shadow-md"
      to={`/destinations/${id}`}
    >
      <div className="relative aspect-[4/3] overflow-hidden bg-ochre/15">
        {imageReference ? (
          <img
            alt={`${name}, ${categoryLabel} in ${city}`}
            className="h-full w-full object-cover transition duration-300 group-hover:scale-105"
            loading="lazy"
            src={imageReference}
          />
        ) : (
          <div
            aria-hidden="true"
            className="flex h-full w-full items-center justify-center bg-gradient-to-br from-ochre/25 to-maroon/20 font-display text-4xl text-maroon/70"
          >
            {name.charAt(0)}
          </div>
        )}
        <span className="absolute left-3 top-3 rounded-full bg-maroon/90 px-3 py-1 text-xs font-semibold text-sand">
          {categoryLabel}
        </span>
        {isHiddenGem ? (
          <span className="absolute right-3 top-3 rounded-full bg-teal px-3 py-1 text-xs font-semibold text-white">
            Hidden gem
          </span>
        ) : null}
      </div>
      <div className="flex flex-1 flex-col gap-2 p-4">
        <h3 className="font-display text-lg font-bold text-maroon group-hover:text-ochre">
          {name}
        </h3>
        <p className="text-sm font-medium text-ink/70">
          {city}, {district}
        </p>
        <p className="line-clamp-3 flex-1 text-sm text-ink/75">{description}</p>
        <RatingStars count={popularity.rating_count} rating={popularity.rating_average} />
      </div>
    </Link>
  );
}
