/**
 * Accessible preview shown when a map marker is selected (Requirement 9.3).
 *
 * Presentational only: it renders the selected marker's minimal details and a
 * real navigation link to the Destination page. The link is a router `Link`
 * (a real anchor) so the navigation action is keyboard-reachable and announced
 * correctly; a close button lets keyboard users dismiss the preview.
 */

import { useId } from 'react';
import { Link } from 'react-router-dom';

import type { MapMarker } from '../../api/types';
import { CATEGORY_LABELS } from '../../lib/catalog';

type MarkerPreviewProps = {
  marker: MapMarker;
  onClose: () => void;
};

export function MarkerPreview({ marker, onClose }: MarkerPreviewProps) {
  const titleId = useId();
  const categoryLabel = CATEGORY_LABELS[marker.category];

  return (
    <aside
      aria-labelledby={titleId}
      className="rounded-2xl border border-gold/30 bg-white p-5 shadow-md"
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-ochre">
            {categoryLabel}
          </p>
          <h3 className="font-display text-xl font-bold text-maroon" id={titleId}>
            {marker.name}
          </h3>
          <p className="text-sm font-medium text-ink/70">
            {marker.city}, {marker.district}
          </p>
        </div>
        <button
          aria-label={`Close ${marker.name} preview`}
          className="rounded-full border border-gold/40 px-3 py-1 text-sm font-semibold text-maroon transition hover:bg-ochre/10"
          onClick={onClose}
          type="button"
        >
          Close
        </button>
      </div>
      <p className="mt-3 line-clamp-3 text-sm text-ink/75">{marker.description}</p>
      <Link
        className="mt-4 inline-flex items-center gap-2 rounded-full bg-teal px-5 py-2.5 font-semibold text-white transition hover:bg-teal/90"
        to={`/destinations/${marker.id}`}
      >
        View destination
        <span aria-hidden="true">→</span>
      </Link>
    </aside>
  );
}
