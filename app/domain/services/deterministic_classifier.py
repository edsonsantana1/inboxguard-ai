"""Classificação determinística aplicada antes de qualquer chamada de IA."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable

from app.domain.entities.classification_candidate import (
    ClassificationCandidate,
)
from app.domain.entities.email_message import EmailMessage
from app.domain.enums.email_category import EmailCategory
from app.domain.enums.email_priority import EmailPriority

_CATEGORY_TERMS: dict[EmailCategory, tuple[str, ...]] = {
    EmailCategory.SUSPICIOUS: (
        "confirme sua senha",
        "validar credenciais",
        "conta bloqueada",
        "acesso suspenso",
        "clique imediatamente",
        "atividade incomum",
        "premio",
        "ganhador",
    ),
    EmailCategory.BILLING: (
        "cobranca",
        "boleto",
        "fatura",
        "vencimento",
        "parcela",
        "debito em aberto",
    ),
    EmailCategory.FINANCIAL: (
        "pagamento",
        "pix",
        "transferencia",
        "banco",
        "nota fiscal",
        "comprovante",
    ),
    EmailCategory.APPOINTMENT: (
        "reuniao",
        "agenda",
        "convite",
        "calendario",
        "compromisso",
        "entrevista",
    ),
    EmailCategory.COLLEGE: (
        "faculdade",
        "atividade",
        "avaliacao",
        "disciplina",
        "professor",
        "senac",
        "nota",
    ),
    EmailCategory.WORK: (
        "projeto",
        "cliente",
        "relatorio",
        "equipe",
        "contrato",
        "ordem de servico",
        "trabalho",
    ),
    EmailCategory.NEWSLETTER: (
        "newsletter",
        "boletim",
        "cancelar inscricao",
        "unsubscribe",
        "descadastrar",
    ),
    EmailCategory.ADVERTISING: (
        "promocao",
        "oferta",
        "desconto",
        "cupom",
        "compre agora",
        "liquidacao",
    ),
    EmailCategory.NOTIFICATION: (
        "notificacao",
        "alerta",
        "verificacao em duas etapas",
        "codigo de seguranca",
        "novo login",
        "confirmacao automatica",
    ),
    EmailCategory.PERSONAL: (
        "familia",
        "amigo",
        "pessoal",
        "aniversario",
    ),
}

_CRITICAL_TERMS = (
    "fraude",
    "conta bloqueada",
    "acesso suspenso",
    "prazo hoje",
    "vence hoje",
    "vencido",
    "vencida",
    "imediatamente",
)

_HIGH_TERMS = (
    "urgente",
    "acao necessaria",
    "prazo",
    "vencimento",
    "responda",
    "pendencia",
)

_REPLY_TERMS = (
    "pode confirmar",
    "por favor responda",
    "preciso de",
    "solicito",
    "retorne",
    "qual horario",
    "quando",
    "?",
)

_RISK_TERMS: dict[str, tuple[str, ...]] = {
    "credential_request": (
        "informe sua senha",
        "envie sua senha",
        "confirme sua senha",
        "compartilhe o codigo",
    ),
    "payment_request": (
        "pix",
        "boleto",
        "pagamento",
        "transferencia",
    ),
    "urgent_language": (
        "urgente",
        "imediatamente",
        "agora",
        "prazo hoje",
    ),
    "suspicious_link_language": (
        "clique aqui",
        "acesse o link",
        "validar conta",
    ),
}


def _normalize(value: str) -> str:
    """Normaliza texto para comparação sem acentos e sem distinção de caixa."""

    decomposed = unicodedata.normalize(
        "NFKD",
        value.casefold(),
    )

    return "".join(character for character in decomposed if not unicodedata.combining(character))


def _compact_whitespace(value: str) -> str:
    """Remove espaços duplicados, quebras de linha e tabulações."""

    return re.sub(r"\s+", " ", value).strip()


def _count_matches(
    text: str,
    terms: Iterable[str],
) -> int:
    """Conta quantos termos configurados aparecem no texto."""

    return sum(1 for term in terms if _normalize(term) in text)


def _contains_any(
    text: str,
    terms: Iterable[str],
) -> bool:
    """Verifica se pelo menos um dos termos aparece no texto."""

    return any(_normalize(term) in text for term in terms)


def _snippet_starts_with_subject(
    subject: str,
    snippet: str,
) -> bool:
    """Verifica se o snippet já começa com o assunto do e-mail."""

    normalized_subject = _normalize(subject)
    normalized_snippet = _normalize(snippet)

    if not normalized_subject:
        return False

    if normalized_snippet == normalized_subject:
        return True

    if not normalized_snippet.startswith(normalized_subject):
        return False

    remaining_text = normalized_snippet[len(normalized_subject) :]

    if not remaining_text:
        return True

    # Evita considerar "Aviso" duplicado em uma palavra como "Avisos".
    return not remaining_text[0].isalnum()


def _join_subject_and_snippet(
    subject: str,
    snippet: str,
) -> str:
    """Une assunto e snippet utilizando pontuação adequada."""

    if subject.endswith((".", "!", "?", ":", ";")):
        return f"{subject} {snippet}"

    return f"{subject}. {snippet}"


def _summary(
    email: EmailMessage,
    *,
    limit: int = 280,
) -> str:
    """Gera um resumo curto sem repetir o assunto no início do snippet."""

    subject = _compact_whitespace(email.subject or "")
    snippet = _compact_whitespace(email.snippet or "")

    if subject and snippet:
        if _snippet_starts_with_subject(subject, snippet):
            source = snippet
        else:
            source = _join_subject_and_snippet(
                subject,
                snippet,
            )
    else:
        source = subject or snippet or "E-mail sem conteúdo textual disponível."

    if len(source) <= limit:
        return source

    truncated = source[: limit - 1].rstrip()

    return f"{truncated}…"


class DeterministicEmailClassifier:
    """Aplica regras transparentes e reproduzíveis sobre metadados seguros."""

    model_name = "deterministic-rules-v1"
    prompt_version = "rules-v1"

    def classify(
        self,
        email: EmailMessage,
    ) -> ClassificationCandidate:
        """Retorna o melhor candidato, inclusive quando inconclusivo."""

        text = _normalize(
            " ".join(
                (
                    email.sender,
                    email.subject,
                    email.snippet,
                    email.body_text or "",
                )
            )
        )

        scores = {
            category: _count_matches(text, terms) for category, terms in _CATEGORY_TERMS.items()
        }

        category, match_count = max(
            scores.items(),
            key=lambda item: item[1],
        )

        no_reply = "no-reply" in text or "noreply" in text or "nao responda" in text

        if match_count == 0:
            category = EmailCategory.UNKNOWN
            confidence = 0.35
        else:
            confidence = min(
                0.98,
                0.68 + (match_count * 0.1),
            )

        if category in {
            EmailCategory.NEWSLETTER,
            EmailCategory.ADVERTISING,
        }:
            priority = EmailPriority.LOW

        elif _contains_any(text, _CRITICAL_TERMS):
            priority = EmailPriority.CRITICAL

        elif _contains_any(text, _HIGH_TERMS):
            priority = EmailPriority.HIGH

        elif category in {
            EmailCategory.FINANCIAL,
            EmailCategory.BILLING,
            EmailCategory.APPOINTMENT,
            EmailCategory.SUSPICIOUS,
        }:
            priority = EmailPriority.MEDIUM

        else:
            priority = EmailPriority.LOW

        requires_reply = (
            not no_reply
            and category
            not in {
                EmailCategory.NEWSLETTER,
                EmailCategory.ADVERTISING,
                EmailCategory.NOTIFICATION,
            }
            and _contains_any(text, _REPLY_TERMS)
        )

        risk_flags = tuple(
            flag for flag, terms in _RISK_TERMS.items() if _contains_any(text, terms)
        )

        matched_label = (
            "nenhuma regra conclusiva" if match_count == 0 else f"{match_count} indicador(es)"
        )

        reason = (
            f"Classificação determinística baseada em {matched_label}; "
            "prioridade derivada de termos explícitos."
        )

        return ClassificationCandidate(
            category=category,
            priority=priority,
            requires_reply=requires_reply,
            confidence=round(confidence, 2),
            summary=_summary(email),
            reason=reason,
            risk_flags=risk_flags,
        )
