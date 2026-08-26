from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from supervisor_ai.core.config import get_settings


def test_mk_operational_migration_upgrade_and_downgrade(
    tmp_path: Path, monkeypatch
) -> None:
    database_path = tmp_path / "mk-operational.sqlite3"
    database_url = f"sqlite+pysqlite:///{database_path}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    get_settings.cache_clear()
    config = Config(str(Path(__file__).parents[2] / "alembic.ini"))

    command.upgrade(config, "head")
    engine = create_engine(database_url)
    inspector = inspect(engine)
    expected = {
        "mk_attendance_mirror",
        "mkbot_conversation_mirror",
        "mk_sync_states",
        "mk_sync_runs",
    }
    assert expected <= set(inspector.get_table_names())
    assert {column["name"] for column in inspector.get_columns("mk_sync_states")} >= {
        "source",
        "entity_type",
        "last_pk",
        "last_success_at",
        "last_attempt_at",
        "status",
        "last_error",
    }
    assert {
        index["name"] for index in inspector.get_indexes("mk_attendance_mirror")
    } >= {
        "ix_mk_attendance_customer_opened",
        "ix_mk_attendance_opened_at",
        "ix_mk_attendance_status",
        "ix_mk_attendance_dialog",
    }

    command.downgrade(config, "20260818_0011")
    assert expected.isdisjoint(inspect(engine).get_table_names())
    command.upgrade(config, "head")
    assert expected <= set(inspect(engine).get_table_names())
    engine.dispose()
    get_settings.cache_clear()
