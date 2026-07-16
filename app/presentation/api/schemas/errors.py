"""Contratos padronizados de erro da API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    """Descrição segura de uma falha retornada ao cliente."""

    code: str
    message: str
    details: list[dict[str, Any]] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    """Envelope de erro com identificador para correlação nos logs."""

    error: ErrorDetail
    request_id: str | None = None
