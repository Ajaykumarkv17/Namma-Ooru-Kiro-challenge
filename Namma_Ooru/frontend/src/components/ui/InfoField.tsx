/**
 * Renders a single labelled Destination fact and enforces the anti-fabrication
 * rule: WHERE a field is null (or an empty string), it shows "Information
 * unavailable" instead of a factual replacement (Requirement 2.3, Data steering).
 * Keeping this in one place guarantees every nullable field renders consistently.
 */

import type { ReactNode } from 'react';

import { INFORMATION_UNAVAILABLE, isUnavailable } from '../../lib/availability';

type InfoFieldProps = {
  label: string;
  /** The source-verified value, or null/undefined when unverified. */
  value: string | number | null | undefined;
  /**
   * Optional renderer for a present value (e.g. a link). Only invoked when a
   * non-empty value exists, so callers never have to guard against null.
   */
  render?: (value: string) => ReactNode;
};

export function InfoField({ label, value, render }: InfoFieldProps) {
  const unavailable = isUnavailable(value);
  const text = unavailable ? '' : String(value);

  return (
    <div className="flex flex-col gap-1">
      <dt className="text-xs font-bold uppercase tracking-[0.14em] text-ochre">{label}</dt>
      <dd className={unavailable ? 'italic text-ink/50' : 'text-ink/85'}>
        {unavailable ? INFORMATION_UNAVAILABLE : render ? render(text) : text}
      </dd>
    </div>
  );
}
