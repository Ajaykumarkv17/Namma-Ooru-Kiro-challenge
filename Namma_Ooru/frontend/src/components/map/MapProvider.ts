/**
 * Replaceable map-rendering abstraction (Requirement 9.4).
 *
 * `MapView` accesses map rendering *only* through this interface, so the concrete
 * library (MapLibre GL today, another provider tomorrow) can be swapped without
 * touching the component. The interface is intentionally minimal and imperative:
 * it owns the map canvas lifecycle (`mount`/`destroy`) and plotting of markers
 * (`renderMarkers`), and reports marker selection back to the component through a
 * callback rather than owning any preview/navigation UI itself (that stays in
 * React so previews and the navigation action are accessible — Requirement 9.3).
 */

import type { MapMarker } from '../../api/types';

/** Geographic center + zoom used to initialize the map view. */
export type MapViewport = {
  longitude: number;
  latitude: number;
  zoom: number;
};

/** Options passed to a provider when the map is first mounted. */
export type MapProviderMountOptions = {
  /** The container element the provider renders its canvas into. */
  container: HTMLElement;
  /** Initial center/zoom. */
  viewport: MapViewport;
  /** Called with the selected marker when a user activates a plotted marker. */
  onMarkerSelect: (marker: MapMarker) => void;
};

/**
 * A swappable map renderer. Implementations must be side-effect free until
 * `mount` is called and must release all resources in `destroy`.
 */
export type MapProvider = {
  /** Human-readable provider name (e.g. "MapLibre GL"), useful for diagnostics. */
  readonly name: string;
  /** Create the map inside `container`; safe to call once per provider instance. */
  mount(options: MapProviderMountOptions): void | Promise<void>;
  /** Replace the plotted markers with `markers` (Requirement 9.1, 9.2). */
  renderMarkers(markers: readonly MapMarker[]): void;
  /** Tear down the map and free all resources. */
  destroy(): void;
};

/** A factory so `MapView` can construct a provider without knowing its class. */
export type MapProviderFactory = () => MapProvider;

/** Tamil Nadu's approximate geographic center, used as the default viewport. */
export const TAMIL_NADU_VIEWPORT: MapViewport = {
  longitude: 78.6569,
  latitude: 11.1271,
  zoom: 6,
};

/**
 * The default provider: a thin lazy adapter that dynamically imports the MapLibre
 * implementation only when the map is actually mounted. Deferring the import keeps
 * the heavy WebGL library (and its module-level browser globals) out of the module
 * graph until it is needed, so `MapView` can be imported and tested with a mock
 * provider without loading MapLibre at all.
 */
export function defaultMapProviderFactory(): MapProvider {
  let delegate: MapProvider | null = null;
  let pendingMarkers: readonly MapMarker[] | null = null;

  return {
    name: 'MapLibre GL (lazy)',
    async mount(options: MapProviderMountOptions): Promise<void> {
      const { createMapLibreMapProvider } = await import('./MapLibreMapProvider');
      delegate = createMapLibreMapProvider();
      await delegate.mount(options);
      if (pendingMarkers) {
        delegate.renderMarkers(pendingMarkers);
        pendingMarkers = null;
      }
    },
    renderMarkers(markers: readonly MapMarker[]): void {
      if (delegate) {
        delegate.renderMarkers(markers);
      } else {
        // Mount is still resolving; remember the latest set to draw on mount.
        pendingMarkers = markers;
      }
    },
    destroy(): void {
      delegate?.destroy();
      delegate = null;
      pendingMarkers = null;
    },
  };
}
