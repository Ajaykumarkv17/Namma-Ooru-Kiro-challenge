# UI/UX Steering — Namma Ooru

## Design principles
- Premium travel aesthetic with a Tamil Nadu cultural identity. Never a generic dashboard.
- Palette inspired by TN: temple gold, kaavi/ochre, deep maroon, coastal teal, warm neutrals.
  All color pairs must meet WCAG AA contrast.
- Large, high-quality imagery on cards and heroes; generous spacing; modern type scale.
- Motion is purposeful (Framer Motion): smooth transitions, no gratuitous animation.

## Component conventions
- Reusable building blocks: `DestinationCard`, `SectionHeader`, `RatingStars`, `ChatWidget`,
  `ItineraryTimeline`, `JourneyPicker`, `MapView`, `Skeleton`, `EmptyState`, `ErrorState`.
- Every data-driven section renders one of: content, skeleton (loading), empty state, error state.
- AI-generated content is visually badged ("AI summary", "AI itinerary") and separated from
  user/source content.

## Responsive behavior
- Mobile-first. Navigation collapses to an accessible menu on small screens.
- Cards reflow to single column on mobile; maps and timelines remain usable by touch.

## Accessibility
- Semantic landmarks (`header`, `nav`, `main`, `footer`), correct heading order.
- All interactive elements keyboard-reachable with visible focus.
- Images have meaningful alt text; icons that convey meaning have labels.
- Full WCAG compliance requires manual testing with assistive tech; automate what we can and note
  the rest.
