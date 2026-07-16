"""Fábrica da aplicação FastAPI e configuração do ciclo de vida."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from time import perf_counter
from uuid import uuid4

import structlog
from fastapi import FastAPI, Request, Response
from starlette.middleware.base import RequestResponseEndpoint
from starlette.middleware.trustedhost import TrustedHostMiddleware
from structlog.contextvars import bind_contextvars, clear_contextvars

from app.core.config import Settings, get_settings
from app.core.logging import configure_logging
from app.core.protocols import DatabaseLifecycle
from app.infrastructure.database import Database
from app.presentation.api.error_handlers import register_exception_handlers
from app.presentation.api.routes.auth import router as auth_router
from app.presentation.api.routes.emails import router as emails_router
from app.presentation.api.routes.health import router as health_router

logger = structlog.get_logger(__name__)


def create_app(
    settings: Settings | None = None,
    database: DatabaseLifecycle | None = None,
) -> FastAPI:
    """Monta a aplicação com dependências substituíveis para facilitar testes."""

    resolved_settings = settings or get_settings()
    configure_logging(resolved_settings)
    resolved_database = database or Database(resolved_settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        """Verifica recursos externos sem derrubar a API por indisponibilidade temporária."""

        logger.info(
            "application_starting",
            environment=resolved_settings.environment,
            version=resolved_settings.app_version,
        )

        if resolved_settings.database_startup_check:
            try:
                latency_ms = await resolved_database.ping()
                logger.info("database_startup_check_succeeded", latency_ms=latency_ms)
            except Exception as exc:  # O endpoint /ready continuará reportando 503.
                logger.warning(
                    "database_startup_check_failed",
                    error_type=type(exc).__name__,
                )

        yield

        await resolved_database.dispose()
        logger.info("application_stopped")

    app = FastAPI(
        title=resolved_settings.app_name,
        version=resolved_settings.app_version,
        description=(
            "InboxGuard AI Fase 3: Gmail, regras determinísticas e classificação "
            "estruturada por IA com fallback e explicabilidade."
        ),
        debug=resolved_settings.debug,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    app.state.settings = resolved_settings
    app.state.database = resolved_database

    if resolved_settings.allowed_hosts != ["*"]:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=resolved_settings.allowed_hosts,
        )

    @app.middleware("http")
    async def request_context_middleware(
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """Adiciona correlação e registra a duração de cada requisição."""

        request_id = request.headers.get("X-Request-ID") or uuid4().hex
        request.state.request_id = request_id
        clear_contextvars()
        bind_contextvars(request_id=request_id, path=request.url.path, method=request.method)
        started_at = perf_counter()

        try:
            response = await call_next(request)
        except Exception:
            logger.exception("request_failed")
            raise
        finally:
            duration_ms = round((perf_counter() - started_at) * 1000, 2)
            logger.info("request_finished", duration_ms=duration_ms)
            clear_contextvars()

        response.headers["X-Request-ID"] = request_id
        return response

    register_exception_handlers(app)
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(emails_router)
    return app
