"""Global error handlers for FastAPI application."""

import logging

from fastapi import Request, status
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)


async def database_error_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    """Handle database errors gracefully."""
    logger.error(f"Database error: {exc}", exc_info=True)

    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "error": "database_unavailable",
            "message": "The database is temporarily unavailable. Please try again later.",
            "details": str(exc) if request.app.debug else None,
        },
    )


async def validation_error_handler(request: Request, exc: ValidationError) -> JSONResponse:
    """Handle Pydantic validation errors."""
    logger.warning(f"Validation error: {exc}")

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "validation_error",
            "message": "Invalid request data",
            "details": exc.errors(),
        },
    )


async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all error handler for unexpected exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "internal_server_error",
            "message": "An unexpected error occurred",
            "details": str(exc) if request.app.debug else None,
        },
    )


def register_error_handlers(app):
    """Register all error handlers with FastAPI app."""
    app.add_exception_handler(SQLAlchemyError, database_error_handler)
    app.add_exception_handler(ValidationError, validation_error_handler)
    app.add_exception_handler(Exception, generic_error_handler)
