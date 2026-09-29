/**
 * A city card that links to its city page. Selecting it navigates to
 * `/cities/:citySlug` with no AI request (Requirement 1.5).
 */

import { Link } from 'react-router-dom';

import type { CitySummary } from '../../lib/catalog';
import { citySlug } from '../../lib/catalog';

type CityCardProps = {
  city: CitySummary;
};

export function CityCard({ city }: CityCardProps) {
  const count = city.destinationCount;
  return (
    <Link
      className="flex flex-col justify-between rounded-2xl border border-gold/25 bg-gradient-to-br from-maroon to-ochre p-5 text-sand shadow-sm transition hover:-translate-y-0.5 hover:shadow-md focus-visible:-translate-y-0.5"
      to={`/cities/${citySlug(city.city)}`}
    >
      <div>
        <h3 className="font-display text-xl font-bold">{city.city}</h3>
        <p className="mt-1 text-sm capitalize text-sand/80">{city.district} district</p>
      </div>
      <p className="mt-6 text-sm font-semibold text-gold">
        {count} {count === 1 ? 'place' : 'places'} to explore
      </p>
    </Link>
  );
}
