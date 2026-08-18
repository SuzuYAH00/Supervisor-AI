from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from supervisor_ai.core.config import get_settings


def test_planned_schedule_migration_round_trip(tmp_path: Path, monkeypatch) -> None:
    database = tmp_path / "planned-schedules.db"
    database_url = f"sqlite+pysqlite:///{database}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    get_settings.cache_clear()
    config = Config("alembic.ini")

    command.upgrade(config, "head")
    tables = set(inspect(create_engine(database_url)).get_table_names())
    assert {
        "collaborator_work_schedules",
        "daily_planned_work_schedules",
        "daily_work_schedule_overrides",
    } <= tables

    command.downgrade(config, "20260818_0010")
    tables = set(inspect(create_engine(database_url)).get_table_names())
    assert "daily_planned_work_schedules" not in tables

    command.upgrade(config, "head")
    assert "daily_planned_work_schedules" in set(
        inspect(create_engine(database_url)).get_table_names()
    )
    get_settings.cache_clear()
