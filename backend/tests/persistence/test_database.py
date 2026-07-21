from sqlalchemy import Engine, text


def test_sqlite_foreign_keys_are_enabled(engine: Engine) -> None:
    with engine.connect() as connection:
        assert connection.scalar(text("PRAGMA foreign_keys")) == 1


def test_database_is_isolated_between_tests(engine: Engine) -> None:
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM commercial_events")) == 0
