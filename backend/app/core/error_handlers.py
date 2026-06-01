"""Global error handlers for FastAPI application."""

import logging
from typing import cast

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)


async def database_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle database errors gracefully."""
    sqlalchemy_error = cast(SQLAlchemyError, exc)
    logger.error(f"Database error: {sqlalchemy_error}", exc_info=True)

    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "error": "database_unavailable",
            "message": "The database is temporarily unavailable. Please try again later.",
            "details": str(sqlalchemy_error) if request.app.debug else None,
        },
    )


async def validation_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle Pydantic validation errors."""
    validation_error = cast(ValidationError, exc)
    logger.warning(f"Validation error: {validation_error}")

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "validation_error",
            "message": "Invalid request data",
            "details": validation_error.errors(),
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


def register_error_handlers(app: FastAPI) -> None:
    """Register all error handlers with FastAPI app."""
    app.add_exception_handler(SQLAlchemyError, database_error_handler)
    app.add_exception_handler(ValidationError, validation_error_handler)
    app.add_exception_handler(Exception, generic_error_handler)
