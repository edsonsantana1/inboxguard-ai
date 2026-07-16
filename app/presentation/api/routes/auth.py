"""Endpoints de autorização Google OAuth 2.0."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.use_cases.complete_google_oauth import CompleteGoogleOAuth
from app.application.use_cases.start_google_oauth import StartGoogleOAuth
from app.core.config import Settings
from app.core.exceptions import (
    ConfigurationError,
    OAuthDeniedError,
    OAuthExchangeError,
)
from app.infrastructure.database.repositories import (
    SQLAlchemyGoogleAccountRepository,
    SQLAlchemyOAuthStateRepository,
)
from app.infrastructure.gmail import GoogleOAuthClient
from app.infrastructure.security import FernetTokenCipher
from app.presentation.api.dependencies import get_session, get_settings_from_request
from app.presentation.api.schemas.oauth import OAuthConnectionResponse

router = APIRouter(prefix="/auth/google", tags=["Google OAuth"])


@router.get(
    "/start",
    response_class=RedirectResponse,
    status_code=307,
    summary="Inicia a autorização da conta Gmail",
)
async def start_google_oauth(
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings_from_request),
) -> RedirectResponse:
    """Redireciona o navegador para a tela de consentimento do Google."""

    use_case = StartGoogleOAuth(
        SQLAlchemyOAuthStateRepository(session),
        GoogleOAuthClient(settings),
        state_ttl_seconds=settings.google_oauth_state_ttl_seconds,
    )
    authorization_url = await use_case.execute()
    return RedirectResponse(authorization_url, status_code=307)


@router.get(
    "/callback",
    response_model=OAuthConnectionResponse,
    summary="Conclui a autorização da conta Gmail",
)
async def complete_google_oauth(
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings_from_request),
) -> OAuthConnectionResponse:
    """Valida state, troca o código e armazena os tokens criptografados."""

    if error:
        raise OAuthDeniedError
    if not code or not state:
        raise OAuthExchangeError
    if not settings.token_encryption_key:
        raise ConfigurationError("Configure TOKEN_ENCRYPTION_KEY antes do OAuth.")

    use_case = CompleteGoogleOAuth(
        SQLAlchemyOAuthStateRepository(session),
        SQLAlchemyGoogleAccountRepository(session),
        GoogleOAuthClient(settings),
        FernetTokenCipher(settings.token_encryption_key),
    )
    account = await use_case.execute(state=state, code=code)
    return OAuthConnectionResponse(email_address=account.email_address)
