/**
 * Thin catalog API client. Encapsulates all network I/O behind typed functions so
 * components and hooks never touch `fetch` directly (Coding steering: data shaping
 * lives in the service/hook layer). Backend errors are surfaced as `ApiError` with
 * a public code and safe message; React Query maps them to error states.
 */

import type {
  ApiErrorBody,
  CityView,
  Destination,
  DestinationDetail,
  DestinationFilters,
  MapFilters,
  MapMarker,
} from './types';

/**
 * Base URL for the backend API. Configured via `VITE_API_BASE_URL` so a local
 * frontend can target the deployed backend; defaults to a relative path for the
 * Vite dev proxy / same-origin deployment.
 */
const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '');

/** Error raised when the backend returns a non-2xx response. */
export class ApiError extends Error {
  readonly status: number;
  readonly code: string;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
  }
}

function buildUrl(path: string, query?: URLSearchParams): string {
  const search = query && [...query].length > 0 ? `?${query.toString()}` : '';
  return `${API_BASE_URL}${path}${search}`;
}

async function request<T>(path: string, query?: URLSearchParams): Promise<T> {
  let response: Response;
  try {
    response = await fetch(buildUrl(path, query), {
      headers: { Accept: 'application/json' },
    });
  } catch {
    // Network / CORS failure: no structured body is available.
    throw new ApiError(0, 'NETWORK_ERROR', 'We could not reach Namma Ooru. Please try again.');
  }

  if (!response.ok) {
    let body: ApiErrorBody = {};
    try {
      body = (await response.json()) as ApiErrorBody;
    } catch {
      body = {};
    }
    throw new ApiError(
      response.status,
      body.error ?? 'REQUEST_FAILED',
      body.detail ?? 'Something went wrong while loading this content.',
    );
  }

  return (await response.json()) as T;
}

function toQuery(filters: DestinationFilters | undefined): URLSearchParams {
  const params = new URLSearchParams();
  if (!filters) {
    return params;
  }
  if (filters.city) {
    params.set('city', filters.city);
  }
  if (filters.district) {
    params.set('district', filters.district);
  }
  if (filters.category) {
    params.set('category', filters.category);
  }
  if (typeof filters.family_friendly === 'boolean') {
    params.set('family_friendly', String(filters.family_friendly));
  }
  if (typeof filters.hidden_gems === 'boolean') {
    params.set('hidden_gems', String(filters.hidden_gems));
  }
  for (const tag of filters.tags ?? []) {
    params.append('tags', tag);
  }
  return params;
}

/** `GET /api/destinations` — every Destination satisfying the active filters. */
export function fetchDestinations(filters?: DestinationFilters): Promise<Destination[]> {
  return request<Destination[]>('/api/destinations', toQuery(filters));
}

/** `GET /api/destinations/{id}` — a Destination with its resolved nearby places. */
export function fetchDestination(id: string): Promise<DestinationDetail> {
  return request<DestinationDetail>(`/api/destinations/${encodeURIComponent(id)}`);
}

/** `GET /api/cities/{city}` — the grouped city overview. */
export function fetchCityView(city: string): Promise<CityView> {
  return request<CityView>(`/api/cities/${encodeURIComponent(city)}`);
}

/**
 * `GET /api/map/markers` — a marker for every filter-matching Destination with
 * verified coordinates. `MapFilters` is the map-relevant subset of the catalog
 * filters, so the shared `toQuery` serializer applies here too.
 */
export function fetchMapMarkers(filters?: MapFilters): Promise<MapMarker[]> {
  return request<MapMarker[]>('/api/map/markers', toQuery(filters));
}
