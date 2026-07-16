"""Ponto de entrada ASGI da aplicação."""

from app.presentation.api.application import create_app

app = create_app()
