"""Testes do parser MIME do Gmail."""

from __future__ import annotations

import base64
from hashlib import sha256

import pytest

from app.infrastructure.gmail.message_parser import parse_gmail_message


def encode(value: str) -> str:
    """Codifica texto no formato base64url usado pelo Gmail."""

    return base64.urlsafe_b64encode(value.encode()).decode().rstrip("=")


def build_message() -> dict[str, object]:
    """Cria uma mensagem multipart mínima e determinística."""

    return {
        "id": "msg-1",
        "threadId": "thread-1",
        "internalDate": "1704067200000",
        "snippet": "Trecho do e-mail",
        "payload": {
            "mimeType": "multipart/alternative",
            "headers": [
                {"name": "From", "value": "Equipe =?UTF-8?Q?T=C3=A9cnica?= <a@example.com>"},
                {"name": "To", "value": "Edson <edson@example.com>"},
                {"name": "Cc", "value": "edson@example.com, Outro <outro@example.com>"},
                {"name": "Subject", "value": "=?UTF-8?Q?Relat=C3=B3rio?="},
            ],
            "parts": [
                {
                    "mimeType": "text/plain",
                    "filename": "",
                    "body": {"data": encode("Texto simples\n\nMensagem")},
                },
                {
                    "mimeType": "text/html",
                    "filename": "",
                    "body": {"data": encode("<p>Texto HTML</p>")},
                },
                {
                    "mimeType": "application/pdf",
                    "filename": "anexo.pdf",
                    "body": {"data": encode("não deve entrar")},
                },
            ],
        },
    }


def test_parser_prefers_plain_text_and_normalizes_headers() -> None:
    email = parse_gmail_message(build_message(), store_body_text=True)

    assert email.provider_message_id == "msg-1"
    assert email.provider_thread_id == "thread-1"
    assert email.sender == "Equipe Técnica <a@example.com>"
    assert email.recipients == (
        "Edson <edson@example.com>",
        "Outro <outro@example.com>",
    )
    assert email.subject == "Relatório"
    assert email.body_text == "Texto simples\n\nMensagem"
    assert email.body_hash == sha256(b"Texto simples\n\nMensagem").hexdigest()
    assert email.received_at.year == 2024


def test_parser_does_not_persist_body_when_privacy_setting_is_false() -> None:
    email = parse_gmail_message(build_message(), store_body_text=False)
    assert email.body_text is None
    assert email.body_hash == sha256(b"Texto simples\n\nMensagem").hexdigest()


def test_parser_uses_html_when_plain_text_is_absent() -> None:
    message = build_message()
    payload = message["payload"]
    assert isinstance(payload, dict)
    payload["parts"] = [
        {
            "mimeType": "text/html",
            "filename": "",
            "body": {"data": encode("<p>Corpo <strong>HTML</strong></p>")},
        }
    ]

    email = parse_gmail_message(message, store_body_text=True)
    assert email.body_text == "Corpo HTML"


def test_parser_uses_snippet_when_message_has_no_body() -> None:
    message = build_message()
    payload = message["payload"]
    assert isinstance(payload, dict)
    payload["parts"] = []

    email = parse_gmail_message(message, store_body_text=True)
    assert email.body_text == ""
    assert email.body_hash == sha256(b"Trecho do e-mail").hexdigest()


def test_parser_rejects_message_without_provider_identifiers() -> None:
    with pytest.raises(ValueError, match="id ou threadId"):
        parse_gmail_message({"payload": {}}, store_body_text=False)
