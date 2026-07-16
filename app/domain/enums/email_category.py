"""Categorias aceitas para classificação de e-mails."""

from enum import StrEnum


class EmailCategory(StrEnum):
    """Categorias de negócio suportadas pelo MVP."""

    WORK = "trabalho"
    FINANCIAL = "financeiro"
    BILLING = "cobrança"
    APPOINTMENT = "compromisso"
    COLLEGE = "faculdade"
    PERSONAL = "pessoal"
    ADVERTISING = "propaganda"
    NEWSLETTER = "newsletter"
    NOTIFICATION = "notificação"
    SUSPICIOUS = "suspeito"
    UNKNOWN = "desconhecido"
