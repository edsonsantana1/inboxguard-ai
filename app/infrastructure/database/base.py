"""Base declarativa e convenções de nomes do SQLAlchemy."""

from __future__ import annotations

from typing import ClassVar

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

# Nomes previsíveis tornam migrações e rollbacks mais seguros em diferentes bancos.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Classe base para todos os modelos persistentes futuros."""

    metadata: ClassVar[MetaData] = MetaData(naming_convention=NAMING_CONVENTION)
