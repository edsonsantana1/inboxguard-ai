"""Validação dos schemas estruturados de classificação."""

import pytest
from pydantic import ValidationError

from app.domain.enums.email_category import EmailCategory
from app.infrastructure.ai.schemas import AIEmailClassificationOutput


def valid_payload() -> dict[str, object]:
    return {
        "category": "trabalho",
        "priority": "high",
        "requires_reply": True,
        "confidence": 0.92,
        "summary": "Cliente solicitou retorno sobre o projeto.",
        "reason": "Há uma solicitação direta e prazo explícito.",
        "risk_flags": ["urgent_language", "urgent_language"],
    }


def test_ai_schema_accepts_and_normalizes_structured_output() -> None:
    result = AIEmailClassificationOutput.model_validate(valid_payload())

    assert result.category is EmailCategory.WORK
    assert result.risk_flags == ["urgent_language"]


def test_ai_schema_rejects_invalid_confidence_and_extra_fields() -> None:
    payload = valid_payload()
    payload["confidence"] = 1.2
    payload["action"] = "send_email"

    with pytest.raises(ValidationError):
        AIEmailClassificationOutput.model_validate(payload)
