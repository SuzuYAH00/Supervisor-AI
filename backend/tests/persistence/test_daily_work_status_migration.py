from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from supervisor_ai.core.config import get_settings


def test_migrations_create_daily_work_status_schema_from_zero(
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
    assert {
        column["name"]
        for column in inspector.get_columns("daily_work_statuses")
    } == {
        "id",
        "collaborator_id",
        "work_date",
        "competence_month",
        "raw_code",
        "source",
        "external_reference",
        "source_sheet",
        "source_cell",
        "created_at",
    }
    index_names = {
        index["name"]
        for index in inspector.get_indexes("daily_work_statuses")
    }
    assert "uq_daily_work_status_source_reference" in index_names
    assert "uq_daily_work_status_collaborator_date" in index_names
    assert inspector.get_foreign_keys("daily_work_statuses")[0][
        "referred_table"
    ] == "operational_collaborator_profiles"
    engine.dispose()
    get_settings.cache_clear()
