"""Endpoints versionados de sincronização, consulta e classificação de e-mails."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.use_cases.classify_email import ClassifyEmail
from app.application.use_cases.get_email import GetEmail
from app.application.use_cases.get_email_classification import GetEmailClassification
from app.application.use_cases.list_emails import ListEmails
from app.application.use_cases.sync_unread_emails import SyncUnreadEmails
from app.core.config import Settings
from app.core.exceptions import ConfigurationError
from app.domain.ports.ai_provider import AIProvider
from app.domain.services.deterministic_classifier import DeterministicEmailClassifier
from app.infrastructure.ai.groq_provider import GroqEmailClassifier
from app.infrastructure.ai.openai_provider import OpenAIEmailClassifier
from app.infrastructure.database.repositories import (
    SQLAlchemyEmailClassificationRepository,
    SQLAlchemyEmailRepository,
    SQLAlchemyGoogleAccountRepository,
)
from app.infrastructure.gmail import GmailClient
from app.infrastructure.security import FernetTokenCipher
from app.presentation.api.dependencies import get_session, get_settings_from_request
from app.presentation.api.schemas.classifications import EmailClassificationResponse
from app.presentation.api.schemas.emails import (
    EmailListResponse,
    EmailResponse,
    EmailSyncResponse,
)

router = APIRouter(prefix="/api/v1/emails", tags=["Emails"])

_NOT_FOUND_RESPONSE = {
    "description": "Recurso não encontrado.",
    "content": {
        "application/json": {
            "example": {
                "error": {
                    "code": "not_found",
                    "message": "E-mail não encontrado.",
                    "details": [],
                },
                "request_id": "exemplo-de-request-id",
            }
        }
    },
}


@router.post(
    "/sync",
    response_model=EmailSyncResponse,
    status_code=status.HTTP_200_OK,
    summary="Sincroniza mensagens não lidas do Gmail",
)
async def sync_emails(
    max_messages: int | None = Query(default=None, ge=1, le=500),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings_from_request),
) -> EmailSyncResponse:
    """Busca e persiste e-mails sem processar novamente mensagens duplicadas."""

    if not settings.token_encryption_key:
        raise ConfigurationError("Configure TOKEN_ENCRYPTION_KEY antes da sincronização.")

    account_repository = SQLAlchemyGoogleAccountRepository(session)
    email_repository = SQLAlchemyEmailRepository(session)
    provider = GmailClient(
        account_repository,
        FernetTokenCipher(settings.token_encryption_key),
        settings,
    )
    use_case = SyncUnreadEmails(account_repository, email_repository, provider)
    limit = max_messages if max_messages is not None else settings.gmail_sync_max_messages
    result = await use_case.execute(limit=limit)
    return EmailSyncResponse(
        found=result.found,
        stored=result.stored,
        duplicates=result.duplicates,
        failed=result.failed,
        failed_message_ids=list(result.failed_message_ids),
    )


@router.get(
    "",
    response_model=EmailListResponse,
    status_code=status.HTTP_200_OK,
    summary="Lista e-mails armazenados",
)
async def list_emails(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> EmailListResponse:
    """Lista metadados ordenados da mensagem mais recente para a mais antiga."""

    page = await ListEmails(SQLAlchemyEmailRepository(session)).execute(
        limit=limit,
        offset=offset,
    )
    return EmailListResponse(
        items=[EmailResponse.from_entity(item) for item in page.items],
        total=page.total,
        limit=page.limit,
        offset=page.offset,
    )


@router.post(
    "/{email_id}/classify",
    response_model=EmailClassificationResponse,
    status_code=status.HTTP_200_OK,
    summary="Classifica e resume um e-mail",
    description=(
        "Aplica regras determinísticas primeiro. A IA só é chamada quando as regras "
        "não atingem o limiar configurado. Resultados existentes são reutilizados."
    ),
    responses={status.HTTP_404_NOT_FOUND: _NOT_FOUND_RESPONSE},
)
async def classify_email(
    email_id: UUID,
    force: bool = Query(default=False, description="Recalcula mesmo quando já existe resultado."),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings_from_request),
) -> EmailClassificationResponse:
    """Executa classificação segura, estruturada e explicável."""

    ai_provider: AIProvider | None = None

    if settings.ai_provider == "openai" and settings.openai_api_key is not None:
        ai_provider = OpenAIEmailClassifier(
            api_key=settings.openai_api_key,
            model=settings.openai_model,
            prompt_version=settings.ai_prompt_version,
            timeout_seconds=settings.ai_timeout_seconds,
            retry_attempts=settings.ai_retry_attempts,
            max_input_characters=settings.ai_max_input_characters,
        )

    elif settings.ai_provider == "groq" and settings.groq_api_key is not None:
        ai_provider = GroqEmailClassifier(
            api_key=settings.groq_api_key,
            base_url=settings.groq_base_url,
            model=settings.groq_model,
            prompt_version=settings.ai_prompt_version,
            timeout_seconds=settings.ai_timeout_seconds,
            retry_attempts=settings.ai_retry_attempts,
            max_input_characters=settings.ai_max_input_characters,
        )
    use_case = ClassifyEmail(
        email_repository=SQLAlchemyEmailRepository(session),
        classification_repository=SQLAlchemyEmailClassificationRepository(session),
        deterministic_classifier=DeterministicEmailClassifier(),
        ai_provider=ai_provider,
        deterministic_threshold=settings.ai_deterministic_threshold,
    )
    classification = await use_case.execute(email_id, force=force)
    return EmailClassificationResponse.from_entity(classification)


@router.get(
    "/{email_id}/classification",
    response_model=EmailClassificationResponse,
    status_code=status.HTTP_200_OK,
    summary="Consulta a classificação de um e-mail",
    responses={status.HTTP_404_NOT_FOUND: _NOT_FOUND_RESPONSE},
)
async def get_email_classification(
    email_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> EmailClassificationResponse:
    """Retorna a classificação atual sem chamar regras ou IA."""

    result = await GetEmailClassification(SQLAlchemyEmailClassificationRepository(session)).execute(
        email_id
    )
    return EmailClassificationResponse.from_entity(result)


@router.get(
    "/{email_id}",
    response_model=EmailResponse,
    status_code=status.HTTP_200_OK,
    summary="Consulta um e-mail armazenado",
    description="Retorna os metadados de um e-mail utilizando seu UUID interno.",
    responses={status.HTTP_404_NOT_FOUND: _NOT_FOUND_RESPONSE},
)
async def get_email(
    email_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> EmailResponse:
    """Retorna os metadados de um e-mail pelo UUID interno."""

    email = await GetEmail(SQLAlchemyEmailRepository(session)).execute(email_id)
    return EmailResponse.from_entity(email)
