from typing import Protocol


class EventRepository(Protocol):
    """Porta reservada para persistência de eventos comerciais."""


class LedgerRepository(Protocol):
    """Porta reservada para persistência de lançamentos do ledger."""


class UnitOfWork(Protocol):
    """Limite transacional reservado para casos de uso com persistência."""
