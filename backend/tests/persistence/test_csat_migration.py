from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from supervisor_ai.core.config import get_settings


def test_migrations_create_csat_schema_from_zero(
    tmp_path: Path, monkeypatch
) -> None:
    database_path = tmp_path / "migrated.sqlite3"
    database_url = f"sqlite+pysqlite:///{database_path}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    get_settings.cache_clear()
    config = Config(str(Path(__file__).parents[2] / "alembic.ini"))

    command.upgrade(config, "head")

    engine = create_engine(database_url)
    inspector = inspect(engine)
    assert "csat_evaluations" in inspector.get_table_names()
    assert {column["name"] for column in inspector.get_columns("csat_evaluations")} == {
        "id",
        "external_reference",
        "source",
        "collaborator_id",
        "channel",
        "score",
        "evaluated_at",
        "created_at",
    }
    index_names = {
        index["name"] for index in inspector.get_indexes("csat_evaluations")
    }
    assert "uq_csat_evaluations_source_reference" in index_names
    assert "attendance_facts" in inspector.get_table_names()
    assert {
        column["name"] for column in inspector.get_columns("attendance_facts")
    } == {
        "id",
        "external_reference",
        "source",
        "customer_code",
        "operator_id",
        "channel",
        "occurred_at",
        "process_code",
        "process_description",
        "opening_code",
        "opening_description",
        "closing_code",
        "closing_description",
        "created_at",
    }
    attendance_indexes = {
        index["name"] for index in inspector.get_indexes("attendance_facts")
    }
    assert "uq_attendance_facts_source_reference" in attendance_indexes
    engine.dispose()
    get_settings.cache_clear()
