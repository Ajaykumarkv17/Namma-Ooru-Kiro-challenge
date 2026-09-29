type FoundationPageProps = {
  eyebrow: string;
  title: string;
  description: string;
};

export function FoundationPage({ eyebrow, title, description }: FoundationPageProps) {
  return (
    <section className="rounded-3xl bg-maroon px-6 py-16 text-sand shadow-lg sm:px-12">
      <p className="text-sm font-bold uppercase tracking-[0.18em] text-gold">{eyebrow}</p>
      <h1 className="mt-4 max-w-3xl font-display text-4xl font-bold leading-tight sm:text-6xl">
        {title}
      </h1>
      <p className="mt-5 max-w-2xl text-lg leading-8 text-sand/90">{description}</p>
    </section>
  );
}
