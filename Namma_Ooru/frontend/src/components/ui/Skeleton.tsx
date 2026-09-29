import type { HTMLAttributes } from 'react';

type SkeletonProps = HTMLAttributes<HTMLDivElement> & {
  label?: string;
};

export function Skeleton({ className = '', label = 'Loading content', ...props }: SkeletonProps) {
  return (
    <div
      aria-label={label}
      aria-live="polite"
      className={`animate-pulse rounded-xl bg-ochre/15 ${className}`.trim()}
      role="status"
      {...props}
    >
      <span className="sr-only">{label}</span>
    </div>
  );
}
