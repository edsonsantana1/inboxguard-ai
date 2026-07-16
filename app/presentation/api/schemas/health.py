"""Schemas dos endpoints de liveness e readiness."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class HealthStatus(StrEnum):
    """Estados operacionais expostos pela API."""

    HEALTHY = "healthy"
    READY = "ready"
    NOT_READY = "not_ready"


class HealthResponse(BaseModel):
    """Resposta de liveness; não depende de serviços externos."""

    status: HealthStatus
    service: str
    version: str
    environment: str
    timestamp: datetime


class ReadinessResponse(BaseModel):
    """Resposta de prontidão com o estado do PostgreSQL."""

    status: HealthStatus
    database: str
    latency_ms: float | None = Field(default=None, ge=0)
    timestamp: datetime
