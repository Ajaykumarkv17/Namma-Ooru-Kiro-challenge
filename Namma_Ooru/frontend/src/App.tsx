import { Navigate, Route, Routes } from 'react-router-dom';

import { AppLayout } from './components/layout/AppLayout';
import { FoundationPage } from './pages/FoundationPage';

export function App() {
  return (
    <AppLayout>
      <Routes>
        <Route
          element={
            <FoundationPage
              description="Discover Tamil Nadu through places, stories, and journeys designed around what matters to you."
              eyebrow="Tamil Nadu travel"
              title="Discover the Tamil Nadu you haven’t seen."
            />
          }
          path="/"
        />
        <Route
          element={
            <FoundationPage
              description="Search will connect you to source-attributed places across Tamil Nadu."
              eyebrow="Plan your discovery"
              title="Find a place that feels like your journey."
            />
          }
          path="/search"
        />
        <Route
          element={
            <FoundationPage
              description="Destination details will provide transparent, source-attributed travel information."
              eyebrow="Destination"
              title="Explore a destination."
            />
          }
          path="/destinations/:destinationId"
        />
        <Route
          element={
            <FoundationPage
              description="City guides will help you explore by interest, pace, and place."
              eyebrow="City guide"
              title="Explore a Tamil Nadu city."
            />
          }
          path="/cities/:citySlug"
        />
        <Route element={<Navigate replace to="/" />} path="*" />
      </Routes>
    </AppLayout>
  );
}
