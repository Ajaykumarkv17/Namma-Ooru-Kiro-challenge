/**
 * Anti-fabrication helpers for nullable Destination facts (Requirement 2.3, Data
 * steering). Kept free of React so components stay component-only and the rule is
 * unit-testable in isolation.
 */

/** The exact copy shown for a null/absent Destination fact (Requirement 2.3). */
export const INFORMATION_UNAVAILABLE = 'Information unavailable';

/** True when a value is absent and should render "Information unavailable". */
export function isUnavailable(value: string | number | null | undefined): boolean {
  if (value === null || value === undefined) {
    return true;
  }
  return typeof value === 'string' && value.trim().length === 0;
}
