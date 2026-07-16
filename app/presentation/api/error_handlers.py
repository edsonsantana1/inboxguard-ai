"""Tratamento centralizado de falhas HTTP sem exposição de detalhes internos."""

from __future__ import annotations

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.exceptions import (
    ConfigurationError,
    ExternalServiceError,
    GmailAccountNotConnectedError,
    InboxGuardError,
    ResourceNotFoundError,
)
from app.presentation.api.schemas.errors import ErrorDetail, ErrorResponse

logger = structlog.get_logger(__name__)


def _request_id(request: Request) -> str | None:
    """Retorna o identificador de correlação quando disponível."""

    return getattr(request.state, "request_id", None)


def _application_error_status(exc: InboxGuardError) -> int:
    """Mapeia erros de aplicação para HTTP sem acoplar o domínio ao FastAPI."""

    if isinstance(exc, ResourceNotFoundError):
        return 404
    if isinstance(exc, GmailAccountNotConnectedError):
        return 409
    if isinstance(exc, ConfigurationError):
        return 503
    if isinstance(exc, ExternalServiceError):
        return 502
    return 400


def register_exception_handlers(app: FastAPI) -> None:
    """Registra handlers consistentes para erros controlados e inesperados."""

    @app.exception_handler(InboxGuardError)
    async def handle_application_error(
        request: Request,
        exc: InboxGuardError,
    ) -> JSONResponse:
        payload = ErrorResponse(
            error=ErrorDetail(code=exc.code, message=exc.message),
            request_id=_request_id(request),
        )
        return JSONResponse(
            status_code=_application_error_status(exc),
            content=payload.model_dump(mode="json"),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        logger.info("request_validation_failed", errors=exc.errors())
        payload = ErrorResponse(
            error=ErrorDetail(
                code="validation_error",
                message="A requisição contém dados inválidos.",
                details=exc.errors(),
            ),
            request_id=_request_id(request),
        )
        return JSONResponse(status_code=422, content=payload.model_dump(mode="json"))

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled_exception", error_type=type(exc).__name__)
        payload = ErrorResponse(
            error=ErrorDetail(
                code="internal_server_error",
                message="Ocorreu um erro interno inesperado.",
            ),
            request_id=_request_id(request),
        )
        return JSONResponse(status_code=500, content=payload.model_dump(mode="json"))
