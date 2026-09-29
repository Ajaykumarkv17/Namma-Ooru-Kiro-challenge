/**
 * Interactive map page (Requirement 9). A thin page wrapper around `MapView`,
 * which owns the map, filters, marker previews, and all data-driven states. The
 * page keeps a single `<main>`-level heading order and a short intro; the map
 * renders through the replaceable `MapProvider` interface.
 */

import { MapView } from '../components/map/MapView';

export function MapPage() {
  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-6 px-4 py-8">
      <MapView />
    </div>
  );
}
