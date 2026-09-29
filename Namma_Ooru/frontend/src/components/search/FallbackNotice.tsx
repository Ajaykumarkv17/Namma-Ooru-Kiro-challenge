/**
 * A clearly visible, accessible notice shown when a search used keyword/tag
 * matching because the AI Provider was unavailable (Requirement 4.3). It surfaces
 * the client-safe `fallback_reason` from the backend and uses `role="status"` so
 * assistive tech announces that results were not AI-interpreted.
 */

import { useId } from 'react';

type FallbackNoticeProps = {
  /** Client-safe reason from the backend; a default is used if it is missing. */
  reason: string | null;
};

const DEFAULT_REASON =
  'AI interpretation is temporarily unavailable; showing keyword and tag matches instead.';

export function FallbackNotice({ reason }: FallbackNoticeProps) {
  const titleId = useId();
  return (
    <div
      aria-labelledby={titleId}
      className="rounded-2xl border border-ochre/50 bg-ochre/10 p-4"
      role="status"
    >
      <div className="flex items-start gap-3">
        <span
          aria-hidden="true"
          className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-ochre text-sm font-bold text-white"
        >
          !
        </span>
        <div>
          <p className="font-semibold text-maroon" id={titleId}>
            Showing keyword and tag matches
          </p>
          <p className="mt-1 text-sm text-ink/80">{reason ?? DEFAULT_REASON}</p>
        </div>
      </div>
    </div>
  );
}
