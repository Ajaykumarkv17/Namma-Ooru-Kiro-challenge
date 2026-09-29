/**
 * Discovery home page (Requirement 1). Renders the hero with search entry and an
 * Explore Tamil Nadu call to action, then catalog-driven sections: popular
 * destinations, personalized discovery (interests, themed journeys, and Surprise
 * Me — Requirement 8), popular cities, categories, hidden gems, and recommended
 * destinations. Catalog data comes from the catalog API and the personalized
 * discovery experiences from the recommendations API, both via React Query; each
 * data-driven section renders one of content, skeleton, empty, or error.
 */

import { useMemo } from 'react';
import { useNavigate } from 'react-router-dom';

import { CatalogSection } from '../components/catalog/CatalogSection';
import { CategoryChips } from '../components/catalog/CategoryChips';
import { CityCard } from '../components/catalog/CityCard';
import { DestinationGrid } from '../components/catalog/DestinationGrid';
import { PersonalizedDiscovery } from '../components/discovery/PersonalizedDiscovery';
import { HomeHero } from '../components/home/HomeHero';
import { useDestinations } from '../hooks/useDestinations';
import {
  selectCategories,
  selectHiddenGems,
  selectPopularCities,
  selectPopularDestinations,
  selectRecommendedDestinations,
} from '../lib/catalog';

export function HomePage() {
  const navigate = useNavigate();
  const query = useDestinations();
  const destinations = useMemo(() => query.data ?? [], [query.data]);

  const state: 'loading' | 'error' | 'ready' = query.isPending
    ? 'loading'
    : query.isError
      ? 'error'
      : 'ready';

  const popular = useMemo(() => selectPopularDestinations(destinations), [destinations]);
  const cities = useMemo(() => selectPopularCities(destinations), [destinations]);
  const categories = useMemo(() => selectCategories(destinations), [destinations]);
  const hiddenGems = useMemo(() => selectHiddenGems(destinations), [destinations]);
  const recommended = useMemo(() => selectRecommendedDestinations(destinations), [destinations]);

  const retry = () => {
    void query.refetch();
  };
  const goToSearch = () => navigate('/search');

  return (
    <div className="space-y-12">
      <HomeHero />

      <div id="explore-tamil-nadu">
        <CatalogSection
          emptyActionLabel="Search destinations"
          emptyDescription="No destinations are available yet. Start a search to discover Tamil Nadu."
          eyebrow="Explore Tamil Nadu"
          headingId="section-popular"
          isEmpty={popular.length === 0}
          onEmptyAction={goToSearch}
          onRetry={retry}
          state={state}
          title="Popular destinations"
        >
          <DestinationGrid destinations={popular} />
        </CatalogSection>
      </div>

      <PersonalizedDiscovery />

      <CatalogSection
        emptyActionLabel="Search destinations"
        emptyDescription="Cities will appear here as destinations are added."
        headingId="section-cities"
        isEmpty={cities.length === 0}
        onEmptyAction={goToSearch}
        onRetry={retry}
        state={state}
        title="Popular cities"
      >
        <ul className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {cities.map((city) => (
            <li className="h-full" key={city.city}>
              <CityCard city={city} />
            </li>
          ))}
        </ul>
      </CatalogSection>

      <CatalogSection
        emptyActionLabel="Search destinations"
        emptyDescription="Categories will appear here as destinations are added."
        headingId="section-categories"
        isEmpty={categories.length === 0}
        onEmptyAction={goToSearch}
        onRetry={retry}
        state={state}
        title="Browse by category"
      >
        <CategoryChips categories={categories} />
      </CatalogSection>

      <CatalogSection
        description="Lesser-known places beyond the usual tourist routes."
        emptyActionLabel="Search destinations"
        emptyDescription="No hidden gems yet — explore the wider catalog to keep discovering."
        eyebrow="Beyond the tourist map"
        headingId="section-hidden-gems"
        isEmpty={hiddenGems.length === 0}
        onEmptyAction={goToSearch}
        onRetry={retry}
        state={state}
        title="Hidden gems"
      >
        <DestinationGrid destinations={hiddenGems} />
      </CatalogSection>

      <CatalogSection
        description="Highly rated places travelers return to."
        emptyActionLabel="Search destinations"
        emptyDescription="Recommendations appear once destinations have visitor ratings."
        headingId="section-recommended"
        isEmpty={recommended.length === 0}
        onEmptyAction={goToSearch}
        onRetry={retry}
        state={state}
        title="Recommended for you"
      >
        <DestinationGrid destinations={recommended} />
      </CatalogSection>
    </div>
  );
}
