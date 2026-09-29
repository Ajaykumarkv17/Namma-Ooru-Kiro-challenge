import { Navigate, Route, Routes } from 'react-router-dom';

import { AppLayout } from './components/layout/AppLayout';
import { CityPage } from './pages/CityPage';
import { DestinationPage } from './pages/DestinationPage';
import { FoundationPage } from './pages/FoundationPage';
import { HomePage } from './pages/HomePage';
import { MapPage } from './pages/MapPage';

export function App() {
  return (
    <AppLayout>
      <Routes>
        <Route element={<HomePage />} path="/" />
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
        <Route element={<DestinationPage />} path="/destinations/:destinationId" />
        <Route element={<CityPage />} path="/cities/:citySlug" />
        <Route element={<MapPage />} path="/map" />
        <Route element={<Navigate replace to="/" />} path="*" />
      </Routes>
    </AppLayout>
  );
}
