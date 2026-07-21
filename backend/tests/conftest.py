from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from supervisor_ai.database.base import Base
from supervisor_ai.infrastructure.persistence.database import (
    create_database_engine,
    create_session_factory,
)
from supervisor_ai.infrastructure.persistence.models import (  # noqa: F401
    CommercialEventRecord,
    LedgerEntryRecord,
    ProcessingRunRecord,
)


@pytest.fixture
def engine(tmp_path: Path) -> Iterator[Engine]:
    database_path = tmp_path / "persistence.sqlite3"
    value = create_database_engine(f"sqlite+pysqlite:///{database_path}")
    Base.metadata.create_all(value)
    yield value
    value.dispose()


@pytest.fixture
def session_factory(engine: Engine) -> sessionmaker[Session]:
    return create_session_factory(engine)
