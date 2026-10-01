import type { ReactNode } from 'react';
import { NavLink } from 'react-router-dom';

import { ChatWidget } from '../chat/ChatWidget';

type AppLayoutProps = {
  children: ReactNode;
};

const navigation = [
  { label: 'Discover', to: '/' },
  { label: 'Search', to: '/search' },
  { label: 'Plan a trip', to: '/itinerary' },
];

export function AppLayout({ children }: AppLayoutProps) {
  return (
    <div className="flex min-h-screen flex-col">
      <header className="border-b border-gold/25 bg-sand">
        <nav
          aria-label="Primary navigation"
          className="mx-auto flex max-w-6xl items-center justify-between px-5 py-4"
        >
          <NavLink className="font-display text-2xl font-bold text-maroon" to="/">
            Namma Ooru
          </NavLink>
          <div className="flex items-center gap-5">
            {navigation.map((item) => (
              <NavLink
                className={({ isActive }) =>
                  `font-semibold ${isActive ? 'text-maroon' : 'text-ink/75 hover:text-maroon'}`
                }
                key={item.to}
                to={item.to}
              >
                {item.label}
              </NavLink>
            ))}
          </div>
        </nav>
      </header>
      <main className="mx-auto w-full max-w-6xl flex-1 space-y-10 px-5 py-10">
        {children}
        <ChatWidget />
      </main>
      <footer className="bg-maroon px-5 py-6 text-center text-sm text-sand">
        Discover the Tamil Nadu you haven&apos;t seen.
      </footer>
    </div>
  );
}
