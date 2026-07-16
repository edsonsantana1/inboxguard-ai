"""Candidato de classificação antes da persistência."""

from dataclasses import dataclass

from app.domain.enums.email_category import EmailCategory
from app.domain.enums.email_priority import EmailPriority


@dataclass(frozen=True, slots=True)
class ClassificationCandidate:
    """Resultado intermediário produzido por regras ou por IA."""

    category: EmailCategory
    priority: EmailPriority
    requires_reply: bool
    confidence: float
    summary: str
    reason: str
    risk_flags: tuple[str, ...] = ()
