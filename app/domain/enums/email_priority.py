"""Prioridades aceitas para classificação de e-mails."""

from enum import StrEnum


class EmailPriority(StrEnum):
    """Níveis de prioridade ordenados por criticidade."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
