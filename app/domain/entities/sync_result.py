"""Resultado agregado da sincronização de mensagens."""

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class SyncResult:
    """Contadores seguros retornados pela sincronização."""

    found: int
    stored: int
    duplicates: int
    failed: int
    failed_message_ids: tuple[str, ...] = field(default_factory=tuple)
