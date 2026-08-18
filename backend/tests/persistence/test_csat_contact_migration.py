from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from supervisor_ai.core.config import get_settings


def test_migrations_create_csat_contacts_from_zero(
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
        column["name"] for column in inspector.get_columns("csat_contacts")
    } == {
        "id",
        "external_reference",
        "source",
        "collaborator_id",
        "external_operator_identity",
        "occurred_on",
        "source_channel",
        "score",
        "source_context",
        "created_at",
    }
    assert {
        index["name"] for index in inspector.get_indexes("csat_contacts")
    } >= {
        "uq_csat_contacts_source_reference",
        "ix_csat_contacts_collaborator_occurred_on",
    }
    assert inspector.get_foreign_keys("csat_contacts")[0]["referred_table"] == (
        "operational_collaborator_profiles"
    )

    command.downgrade(config, "20260817_0006")
    assert "csat_contacts" not in inspect(engine).get_table_names()
    command.upgrade(config, "head")
    assert "csat_contacts" in inspect(engine).get_table_names()
    engine.dispose()
    get_settings.cache_clear()
