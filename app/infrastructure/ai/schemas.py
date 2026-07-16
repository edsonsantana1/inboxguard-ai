"""Schemas estritos usados para validar a saída do provedor de IA."""

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.enums.email_category import EmailCategory
from app.domain.enums.email_priority import EmailPriority


class AIEmailClassificationOutput(BaseModel):
    """Contrato estruturado aceito da IA; campos extras são rejeitados."""

    model_config = ConfigDict(extra="forbid")

    category: EmailCategory
    priority: EmailPriority
    requires_reply: bool
    confidence: float = Field(ge=0, le=1)
    summary: str = Field(min_length=1, max_length=500)
    reason: str = Field(min_length=1, max_length=500)
    risk_flags: list[str] = Field(max_length=12)

    @field_validator("risk_flags")
    @classmethod
    def normalize_flags(cls, value: list[str]) -> list[str]:
        return list(dict.fromkeys(flag.strip()[:64] for flag in value if flag.strip()))
