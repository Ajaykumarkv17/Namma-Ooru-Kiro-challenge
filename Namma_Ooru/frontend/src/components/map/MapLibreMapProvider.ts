/**
 * MapLibre GL implementation of the `MapProvider` interface (Requirement 9.4).
 *
 * This is the first concrete provider. It owns a MapLibre `Map` instance and a
 * set of `Marker`s. `MapView` never imports MapLibre directly — it only talks to
 * the `MapProvider` interface — so this file is the single seam where the map
 * library lives and can be swapped for another provider.
 *
 * Marker selection is surfaced through the `onMarkerSelect` callback so the React
 * layer renders the accessible preview + navigation action (Requirement 9.3);
 * the provider does not own any preview UI.
 */

import maplibregl, { type Map as MapLibreMap, Marker } from 'maplibre-gl';

import type { MapMarker } from '../../api/types';
import type { MapProvider, MapProviderMountOptions } from './MapProvider';

/**
 * A free, key-less raster style (OpenStreetMap tiles) so the map renders without
 * requiring an API key. Swap via a provider constructed with a different style.
 */
const DEFAULT_STYLE: maplibregl.StyleSpecification = {
  version: 8,
  sources: {
    osm: {
      type: 'raster',
      tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
      tileSize: 256,
      attribution: '© OpenStreetMap contributors',
    },
  },
  layers: [{ id: 'osm', type: 'raster', source: 'osm' }],
};

export class MapLibreMapProvider implements MapProvider {
  readonly name = 'MapLibre GL';

  private map: MapLibreMap | null = null;
  private markers: Marker[] = [];
  private readonly styleSpec: maplibregl.StyleSpecification;

  constructor(styleSpec: maplibregl.StyleSpecification = DEFAULT_STYLE) {
    this.styleSpec = styleSpec;
  }

  mount({ container, viewport, onMarkerSelect }: MapProviderMountOptions): void {
    this.map = new maplibregl.Map({
      container,
      style: this.styleSpec,
      center: [viewport.longitude, viewport.latitude],
      zoom: viewport.zoom,
    });
    this.onMarkerSelect = onMarkerSelect;
  }

  renderMarkers(markers: readonly MapMarker[]): void {
    const map = this.map;
    if (!map) {
      return;
    }
    // Clear the previously plotted markers before drawing the new set so filter
    // changes never leave stale markers behind.
    for (const marker of this.markers) {
      marker.remove();
    }
    this.markers = markers.map((data) => {
      const element = this.createMarkerElement(data);
      return new Marker({ element }).setLngLat([data.longitude, data.latitude]).addTo(map);
    });
  }

  destroy(): void {
    for (const marker of this.markers) {
      marker.remove();
    }
    this.markers = [];
    this.map?.remove();
    this.map = null;
  }

  private onMarkerSelect: (marker: MapMarker) => void = () => {};

  /** Build a keyboard-activatable marker element that reports selection. */
  private createMarkerElement(data: MapMarker): HTMLButtonElement {
    const element = document.createElement('button');
    element.type = 'button';
    element.className = 'namma-map-marker';
    element.setAttribute('aria-label', `${data.name}, ${data.city}`);
    element.addEventListener('click', () => this.onMarkerSelect(data));
    return element;
  }
}

/** Factory matching `MapProviderFactory` for `MapView`'s default provider. */
export function createMapLibreMapProvider(): MapProvider {
  return new MapLibreMapProvider();
}
