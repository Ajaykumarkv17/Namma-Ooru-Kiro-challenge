"""Safe, structured API errors and centralized FastAPI exception mapping."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class DomainError(Exception):
    """Expected failure with a public code and client-safe message."""

    status_code = 422
    error_code = "BUSINESS_RULE_VIOLATION"
    public_detail = "The request could not be completed."

    def __init__(self, detail: str | None = None) -> None:
        self.detail = detail or self.public_detail
        super().__init__(self.detail)


class DependencyUnavailableError(DomainError):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    error_code = "AI_UNAVAILABLE"
    public_detail = "The requested service is temporarily unavailable."


class NotFoundError(DomainError):
    status_code = status.HTTP_404_NOT_FOUND
    error_code = "NOT_FOUND"
    public_detail = "The requested resource was not found."


class DestinationNotFoundError(NotFoundError):
    """A requested Destination id does not exist in the catalog (Requirement 11.3)."""

    error_code = "DESTINATION_NOT_FOUND"
    public_detail = "The requested destination was not found."


def _error_body(error: str, detail: Any) -> dict[str, Any]:
    return {"error": error, "detail": detail}


def register_exception_handlers(app: FastAPI) -> None:
    """Register the single translation layer from expected failures to HTTP errors."""

    @app.exception_handler(RequestValidationError)
    async def request_validation_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        del request
        fields = [
            {
                "field": ".".join(str(part) for part in item["loc"]),
                "message": item["msg"],
            }
            for item in exc.errors()
        ]
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=_error_body("VALIDATION_ERROR", fields),
        )

    @app.exception_handler(DomainError)
    async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
        del request
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body(exc.error_code, exc.detail),
        )

    @app.exception_handler(Exception)
    async def internal_error_handler(request: Request, exc: Exception) -> JSONResponse:
        del request, exc
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_error_body("INTERNAL_ERROR", "An unexpected error occurred."),
        )
