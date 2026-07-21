from types import TracebackType

from sqlalchemy.orm import Session, sessionmaker

from supervisor_ai.infrastructure.persistence.repositories import (
    SqlAlchemyEventRepository,
    SqlAlchemyLedgerRepository,
    SqlAlchemyProcessingRunRepository,
)


class SqlAlchemyUnitOfWork:
    """Transação explícita; sair sem commit sempre descarta as alterações."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory
        self._session: Session | None = None

    def __enter__(self) -> "SqlAlchemyUnitOfWork":
        if self._session is not None:
            raise RuntimeError("unit of work is already active")
        session = self._session_factory()
        self._session = session
        self.events = SqlAlchemyEventRepository(session)
        self.processing_runs = SqlAlchemyProcessingRunRepository(session)
        self.ledger = SqlAlchemyLedgerRepository(session)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        del exc_value, traceback
        session = self._require_session()
        try:
            if exc_type is not None or session.in_transaction():
                session.rollback()
        finally:
            session.close()
            self._session = None

    def commit(self) -> None:
        self._require_session().commit()

    def rollback(self) -> None:
        self._require_session().rollback()

    def _require_session(self) -> Session:
        if self._session is None:
            raise RuntimeError("unit of work is not active")
        return self._session
