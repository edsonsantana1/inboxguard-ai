"""Estados internos de uma mensagem persistida."""

from enum import StrEnum


class EmailStatus(StrEnum):
    """Estados permitidos antes das fases de classificação e resposta."""

    PENDING = "pending"
    PROCESSED = "processed"
    IGNORED = "ignored"
