"""Conversão do payload MIME do Gmail para a entidade EmailMessage."""

from __future__ import annotations

import base64
from datetime import UTC, datetime
from email.header import decode_header, make_header
from email.utils import getaddresses, parsedate_to_datetime
from hashlib import sha256
from typing import Any

from app.domain.entities.email_message import EmailMessage
from app.infrastructure.gmail.html_normalizer import html_to_text, normalize_plain_text


def _decode_header_value(value: str | None, *, default: str = "") -> str:
    """Decodifica cabeçalhos RFC 2047 sem falhar a mensagem inteira."""

    if not value:
        return default
    try:
        return str(make_header(decode_header(value))).strip() or default
    except (LookupError, UnicodeError):
        return value.strip() or default


def _decode_base64url(value: str | None) -> str:
    """Decodifica corpo base64url usando substituição para bytes inválidos."""

    if not value:
        return ""
    padded = value + "=" * (-len(value) % 4)
    try:
        raw = base64.urlsafe_b64decode(padded.encode("ascii"))
    except (ValueError, UnicodeEncodeError):
        return ""
    return raw.decode("utf-8", errors="replace")


def _headers(payload: dict[str, Any]) -> dict[str, str]:
    """Cria mapa case-insensitive dos cabeçalhos relevantes."""

    result: dict[str, str] = {}
    for item in payload.get("headers", []):
        name = str(item.get("name", "")).lower()
        value = str(item.get("value", ""))
        if name:
            result[name] = value
    return result


def _collect_text_parts(part: dict[str, Any]) -> tuple[list[str], list[str]]:
    """Percorre MIME recursivamente e separa texto simples de HTML."""

    plain: list[str] = []
    html: list[str] = []
    mime_type = str(part.get("mimeType", "")).lower()
    filename = str(part.get("filename", ""))
    body = part.get("body", {})

    if not filename:
        decoded = _decode_base64url(body.get("data"))
        if decoded:
            if mime_type == "text/plain":
                plain.append(decoded)
            elif mime_type == "text/html":
                html.append(decoded)

    for child in part.get("parts", []) or []:
        child_plain, child_html = _collect_text_parts(child)
        plain.extend(child_plain)
        html.extend(child_html)

    return plain, html


def _parse_recipients(headers: dict[str, str]) -> tuple[str, ...]:
    """Normaliza destinatários To/Cc para endereços sem duplicidade."""

    raw_values = [headers.get("to", ""), headers.get("cc", "")]
    recipients: list[str] = []
    seen: set[str] = set()
    for name, address in getaddresses(raw_values):
        normalized_address = address.strip().lower()
        if not normalized_address or normalized_address in seen:
            continue
        seen.add(normalized_address)
        display_name = _decode_header_value(name)
        recipients.append(
            f"{display_name} <{normalized_address}>" if display_name else normalized_address
        )
    return tuple(recipients)


def _parse_received_at(message: dict[str, Any], headers: dict[str, str]) -> datetime:
    """Usa internalDate do Gmail e recorre ao cabeçalho Date quando necessário."""

    internal_date = message.get("internalDate")
    if internal_date:
        try:
            return datetime.fromtimestamp(int(internal_date) / 1000, tz=UTC)
        except (TypeError, ValueError, OSError):
            pass

    raw_date = headers.get("date")
    if raw_date:
        try:
            parsed = parsedate_to_datetime(raw_date)
            return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)
        except (TypeError, ValueError, OverflowError):
            pass

    return datetime.now(UTC)


def parse_gmail_message(
    message: dict[str, Any],
    *,
    store_body_text: bool,
) -> EmailMessage:
    """Valida campos mínimos, normaliza MIME e calcula hash do conteúdo."""

    message_id = str(message.get("id", "")).strip()
    thread_id = str(message.get("threadId", "")).strip()
    if not message_id or not thread_id:
        raise ValueError("Mensagem Gmail sem id ou threadId.")

    payload = message.get("payload") or {}
    headers = _headers(payload)
    plain_parts, html_parts = _collect_text_parts(payload)

    if plain_parts:
        normalized_body = normalize_plain_text("\n\n".join(plain_parts))
    elif html_parts:
        normalized_body = html_to_text("\n\n".join(html_parts))
    else:
        normalized_body = ""

    snippet = normalize_plain_text(str(message.get("snippet", "")))
    hash_source = normalized_body or snippet

    return EmailMessage(
        provider_message_id=message_id,
        provider_thread_id=thread_id,
        sender=_decode_header_value(headers.get("from"), default="(remetente desconhecido)"),
        recipients=_parse_recipients(headers),
        subject=_decode_header_value(headers.get("subject"), default="(sem assunto)"),
        received_at=_parse_received_at(message, headers),
        snippet=snippet,
        body_text=normalized_body if store_body_text else None,
        body_hash=sha256(hash_source.encode("utf-8")).hexdigest(),
    )
