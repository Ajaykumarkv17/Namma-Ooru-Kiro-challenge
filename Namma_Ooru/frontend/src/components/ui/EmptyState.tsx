import { useId, type ReactNode } from 'react';

type EmptyStateProps = {
  title: string;
  description: string;
  action?: ReactNode;
};

export function EmptyState({ title, description, action }: EmptyStateProps) {
  const titleId = useId();
  return (
    <div
      aria-labelledby={titleId}
      className="rounded-2xl border border-gold/30 bg-white p-8 text-center shadow-sm"
      role="group"
    >
      <p aria-hidden="true" className="mb-3 text-3xl text-ochre">
        ✦
      </p>
      <h2 className="font-display text-2xl font-bold text-maroon" id={titleId}>
        {title}
      </h2>
      <p className="mx-auto mt-2 max-w-prose text-ink/75">{description}</p>
      {action ? <div className="mt-5">{action}</div> : null}
    </div>
  );
}
