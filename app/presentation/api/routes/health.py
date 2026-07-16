"""Endpoints operacionais para liveness e readiness."""

from __future__ import annotations

from datetime import UTC, datetime

import structlog
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.core.config import Settings
from app.core.protocols import DatabaseLifecycle
from app.presentation.api.dependencies import get_database, get_settings_from_request
from app.presentation.api.schemas.health import (
    HealthResponse,
    HealthStatus,
    ReadinessResponse,
)

router = APIRouter(tags=["Operations"])
logger = structlog.get_logger(__name__)


@router.get("/health", response_model=HealthResponse, summary="Verifica se a API está viva")
async def health(
    settings: Settings = Depends(get_settings_from_request),
) -> HealthResponse:
    """Retorna 200 enquanto o processo da aplicação estiver respondendo."""

    return HealthResponse(
        status=HealthStatus.HEALTHY,
        service=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
        timestamp=datetime.now(UTC),
    )


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    responses={503: {"model": ReadinessResponse}},
    summary="Verifica se a API está pronta para receber tráfego",
)
async def ready(
    database: DatabaseLifecycle = Depends(get_database),
) -> ReadinessResponse | JSONResponse:
    """Valida o PostgreSQL sem transformar indisponibilidade em erro não tratado."""

    try:
        latency_ms = await database.ping()
    except Exception as exc:
        logger.warning("database_readiness_failed", error_type=type(exc).__name__)
        payload = ReadinessResponse(
            status=HealthStatus.NOT_READY,
            database="unavailable",
            timestamp=datetime.now(UTC),
        )
        return JSONResponse(status_code=503, content=payload.model_dump(mode="json"))

    return ReadinessResponse(
        status=HealthStatus.READY,
        database="available",
        latency_ms=latency_ms,
        timestamp=datetime.now(UTC),
    )
