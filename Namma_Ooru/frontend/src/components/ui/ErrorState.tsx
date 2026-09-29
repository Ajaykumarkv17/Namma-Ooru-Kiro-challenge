type ErrorStateProps = {
  title?: string;
  message: string;
  onRetry?: () => void;
  retryLabel?: string;
};

export function ErrorState({
  title = 'We could not load this right now',
  message,
  onRetry,
  retryLabel = 'Try again',
}: ErrorStateProps) {
  return (
    <section
      aria-labelledby="error-state-title"
      className="rounded-2xl border border-maroon/30 bg-white p-8 text-center shadow-sm"
      role="alert"
    >
      <h2 className="font-display text-2xl font-bold text-maroon" id="error-state-title">
        {title}
      </h2>
      <p className="mx-auto mt-2 max-w-prose text-ink/75">{message}</p>
      {onRetry ? (
        <button
          className="mt-5 rounded-full bg-teal px-5 py-2.5 font-semibold text-white transition hover:bg-teal/90"
          onClick={onRetry}
          type="button"
        >
          {retryLabel}
        </button>
      ) : null}
    </section>
  );
}
