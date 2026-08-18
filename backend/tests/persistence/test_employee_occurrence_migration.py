from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from supervisor_ai.core.config import get_settings


def test_employee_occurrence_migration_from_empty_database(
    tmp_path: Path, monkeypatch
) -> None:
    database_path = tmp_path / "migration.sqlite3"
    database_url = f"sqlite+pysqlite:///{database_path}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    get_settings.cache_clear()
    config = Config(str(Path(__file__).parents[2] / "alembic.ini"))

    command.upgrade(config, "head")

    engine = create_engine(database_url)
    inspector = inspect(engine)
    assert "employee_occurrence_reports" in inspector.get_table_names()
    assert {
        "id",
        "external_reference",
        "source",
        "collaborator_id",
        "external_collaborator_identity",
        "submitted_at",
        "occurrence_date",
        "reason_text",
        "source_sheet",
        "source_row",
        "created_at",
    } == {
        column["name"]
        for column in inspector.get_columns("employee_occurrence_reports")
    }
    indexes = {
        index["name"]: index
        for index in inspector.get_indexes("employee_occurrence_reports")
    }
    assert indexes["uq_employee_occurrence_reports_source_reference"]["unique"]
    assert "ix_employee_occurrence_reports_collaborator_date" in indexes
    engine.dispose()
    get_settings.cache_clear()
