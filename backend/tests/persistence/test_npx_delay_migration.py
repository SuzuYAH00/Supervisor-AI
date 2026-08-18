from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from supervisor_ai.core.config import get_settings


def test_npx_delay_migration_from_empty_database(tmp_path: Path, monkeypatch) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'delay.sqlite3'}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    get_settings.cache_clear()
    config = Config(str(Path(__file__).parents[2] / "alembic.ini"))
    command.upgrade(config, "head")
    tables = set(inspect(create_engine(database_url)).get_table_names())
    assert {
        "work_session_facts",
        "pause_facts",
        "delay_occurrences",
        "delay_reviews",
    } <= tables
    get_settings.cache_clear()
