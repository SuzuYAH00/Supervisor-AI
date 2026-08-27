from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from supervisor_ai.core.config import get_settings


def test_commercial_migration_upgrade_downgrade_upgrade(
    tmp_path: Path, monkeypatch
) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'commercial.sqlite3'}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    get_settings.cache_clear()
    config = Config(str(Path(__file__).parents[2] / "alembic.ini"))
    engine = create_engine(database_url)
    commercial = {
        "mk_contract_mirror",
        "mk_plan_mirror",
        "mk_contract_plan_change_mirror",
    }

    command.upgrade(config, "head")
    assert commercial <= set(inspect(engine).get_table_names())
    command.downgrade(config, "20260826_0012")
    tables = set(inspect(engine).get_table_names())
    assert commercial.isdisjoint(tables)
    assert {"mk_attendance_mirror", "mk_sync_states"} <= tables
    command.upgrade(config, "head")
    assert commercial <= set(inspect(engine).get_table_names())

    engine.dispose()
    get_settings.cache_clear()
