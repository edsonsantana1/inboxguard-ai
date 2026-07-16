"""Origem de uma classificação persistida."""

from enum import StrEnum


class ClassificationSource(StrEnum):
    """Identifica como a classificação foi obtida."""

    DETERMINISTIC = "deterministic"
    AI = "ai"
    FALLBACK = "fallback"
