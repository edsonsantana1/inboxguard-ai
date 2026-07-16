"""Porta para provedores de inteligência artificial."""

from typing import Protocol

from app.domain.entities.classification_candidate import ClassificationCandidate
from app.domain.entities.email_message import EmailMessage


class AIProvider(Protocol):
    """Contrato mínimo para classificação estruturada de e-mails."""

    @property
    def model_name(self) -> str:
        """Retorna o identificador público do modelo configurado."""
        raise NotImplementedError

    @property
    def prompt_version(self) -> str:
        """Retorna a versão das regras enviadas ao modelo."""
        raise NotImplementedError

    async def classify_email(self, email: EmailMessage) -> ClassificationCandidate:
        """Classifica uma mensagem sem executar ações sobre ela."""
        raise NotImplementedError
