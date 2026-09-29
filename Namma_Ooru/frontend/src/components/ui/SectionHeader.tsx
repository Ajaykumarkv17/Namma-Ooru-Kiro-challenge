/**
 * Section heading with an optional eyebrow and trailing action (e.g. a "view all"
 * link). Renders a real `<h2>` so the home page keeps a correct heading order
 * beneath the hero `<h1>` (Accessibility steering).
 */

import type { ReactNode } from 'react';

type SectionHeaderProps = {
  title: string;
  eyebrow?: string;
  description?: string;
  action?: ReactNode;
  /** Id applied to the heading so a section can be labelled by it. */
  headingId?: string;
};

export function SectionHeader({
  title,
  eyebrow,
  description,
  action,
  headingId,
}: SectionHeaderProps) {
  return (
    <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
      <div>
        {eyebrow ? (
          <p className="text-xs font-bold uppercase tracking-[0.18em] text-ochre">{eyebrow}</p>
        ) : null}
        <h2 className="font-display text-2xl font-bold text-maroon sm:text-3xl" id={headingId}>
          {title}
        </h2>
        {description ? <p className="mt-1 max-w-2xl text-ink/70">{description}</p> : null}
      </div>
      {action ? <div className="shrink-0">{action}</div> : null}
    </div>
  );
}
