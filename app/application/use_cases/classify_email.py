"""Caso de uso para classificação explicável de uma mensagem."""

from __future__ import annotations

from uuid import UUID

import structlog

from app.core.exceptions import ResourceNotFoundError
from app.domain.entities.email_classification import EmailClassification
from app.domain.enums.classification_source import ClassificationSource
from app.domain.ports.ai_provider import AIProvider
from app.domain.ports.repositories import EmailClassificationRepository, EmailRepository
from app.domain.services.deterministic_classifier import DeterministicEmailClassifier

logger = structlog.get_logger(__name__)


class ClassifyEmail:
    """Combina regras, IA opcional, fallback e persistência idempotente."""

    def __init__(
        self,
        email_repository: EmailRepository,
        classification_repository: EmailClassificationRepository,
        deterministic_classifier: DeterministicEmailClassifier,
        ai_provider: AIProvider | None,
        *,
        deterministic_threshold: float,
    ) -> None:
        self._email_repository = email_repository
        self._classification_repository = classification_repository
        self._deterministic_classifier = deterministic_classifier
        self._ai_provider = ai_provider
        self._deterministic_threshold = deterministic_threshold

    async def execute(self, email_id: UUID, *, force: bool = False) -> EmailClassification:
        """Classifica uma mensagem sem repetir custo de IA quando já existe resultado."""

        if not force:
            existing = await self._classification_repository.get_by_email_id(email_id)
            if existing is not None:
                return existing

        email = await self._email_repository.get_by_id(email_id)
        if email is None:
            raise ResourceNotFoundError("E-mail")

        deterministic = self._deterministic_classifier.classify(email)
        candidate = deterministic
        source = ClassificationSource.DETERMINISTIC
        model_name = self._deterministic_classifier.model_name
        prompt_version = self._deterministic_classifier.prompt_version

        should_use_ai = deterministic.confidence < self._deterministic_threshold
        if should_use_ai and self._ai_provider is not None:
            try:
                candidate = await self._ai_provider.classify_email(email)
                source = ClassificationSource.AI
                model_name = self._ai_provider.model_name
                prompt_version = self._ai_provider.prompt_version
            except Exception as exc:
                logger.warning("ai_classification_fallback", error_type=type(exc).__name__)
                source = ClassificationSource.FALLBACK
                model_name = self._deterministic_classifier.model_name
                prompt_version = self._deterministic_classifier.prompt_version

        classification = EmailClassification(
            email_id=email_id,
            category=candidate.category,
            priority=candidate.priority,
            requires_reply=candidate.requires_reply,
            confidence=candidate.confidence,
            summary=candidate.summary,
            reason=candidate.reason,
            risk_flags=candidate.risk_flags,
            source=source,
            model_name=model_name,
            prompt_version=prompt_version,
        )
        return await self._classification_repository.upsert(classification)
