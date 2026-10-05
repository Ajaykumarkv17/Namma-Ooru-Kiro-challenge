"""AWS Lambda adapter for the Namma Ooru FastAPI application."""

from __future__ import annotations

from mangum import Mangum  # type: ignore[import-not-found]

from app.main import app

handler = Mangum(app, lifespan="off")
