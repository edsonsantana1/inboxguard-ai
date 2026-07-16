"""Caso de uso para consultar a classificação de um e-mail."""

from uuid import UUID

from app.core.exceptions import ResourceNotFoundError
from app.domain.entities.email_classification import EmailClassification
from app.domain.ports.repositories import EmailClassificationRepository


class GetEmailClassification:
    """Consulta a classificação persistida pelo ID do e-mail."""

    def __init__(self, repository: EmailClassificationRepository) -> None:
        self._repository = repository

    async def execute(self, email_id: UUID) -> EmailClassification:
        classification = await self._repository.get_by_email_id(email_id)
        if classification is None:
            raise ResourceNotFoundError("Classificação")
        return classification
