"""Deterministic itinerary domain: models, scheduling, and structured edit ops.

This package holds the pure, I/O-free itinerary core. Task 5.1 establishes the
data models (``Itinerary``, ``ItineraryDay``, ``ItineraryActivity``, the trip
``ItineraryConstraints``, and the structured ``ItineraryOperation`` edit ops).
Later tasks add ``ItineraryService`` generation (5.2) and operations (5.3) on top
of these models. Nothing here performs I/O or AWS calls, so the whole domain is
unit- and property-testable without live AWS (architecture steering).
"""
