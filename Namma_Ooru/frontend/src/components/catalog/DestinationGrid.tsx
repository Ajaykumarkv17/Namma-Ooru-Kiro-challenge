/**
 * Responsive grid of destination cards. Reflows to a single column on mobile and
 * expands to multiple columns on larger screens (UI/UX steering: mobile-first).
 */

import type { Destination } from '../../api/types';
import { DestinationCard } from './DestinationCard';

type DestinationGridProps = {
  destinations: readonly Destination[];
};

export function DestinationGrid({ destinations }: DestinationGridProps) {
  return (
    <ul className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
      {destinations.map((destination) => (
        <li className="h-full" key={destination.id}>
          <DestinationCard destination={destination} />
        </li>
      ))}
    </ul>
  );
}
