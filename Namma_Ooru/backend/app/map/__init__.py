"""Interactive Tamil Nadu map: models, deterministic marker service, and router.

The map feature (Requirement 9) exposes a filtered set of ``MapMarker`` records
for the frontend ``MapProvider`` to render. The marker-shaping lives in a pure
``MapMarkerService`` (``app.map.service``) so it is unit- and property-testable
(Property 12) without any I/O; the router (``app.map.router``) is thin and only
binds/validates input and delegates to the repository plus the service.
"""
