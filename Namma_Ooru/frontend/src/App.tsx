import { Navigate, Route, Routes } from 'react-router-dom';

import { AppLayout } from './components/layout/AppLayout';
import { CityPage } from './pages/CityPage';
import { DestinationPage } from './pages/DestinationPage';
import { HomePage } from './pages/HomePage';
import { ItineraryPlannerPage } from './pages/ItineraryPlannerPage';
import { MapPage } from './pages/MapPage';
import { SearchPage } from './pages/SearchPage';

export function App() {
  return (
    <AppLayout>
      <Routes>
        <Route element={<HomePage />} path="/" />
        <Route element={<SearchPage />} path="/search" />
        <Route element={<DestinationPage />} path="/destinations/:destinationId" />
        <Route element={<CityPage />} path="/cities/:citySlug" />
        <Route element={<MapPage />} path="/map" />
        <Route element={<ItineraryPlannerPage />} path="/itinerary" />
        <Route element={<Navigate replace to="/" />} path="*" />
      </Routes>
    </AppLayout>
  );
}
