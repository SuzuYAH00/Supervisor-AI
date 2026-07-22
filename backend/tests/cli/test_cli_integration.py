import io
import subprocess
import sys
from pathlib import Path

from sqlalchemy import Engine

from supervisor_ai.bootstrap import build_session_factory, build_unit_of_work_factory
from supervisor_ai.cli.main import CliExitCode, main
from supervisor_ai.database.base import Base
from tests.importing.csv_factories import csv_row, csv_text


def prepared_database(tmp_path: Path, name: str) -> tuple[str, Engine]:
    database_url = f"sqlite+pysqlite:///{tmp_path / name}"
    session_factory = build_session_factory(database_url)
    engine = session_factory.kw["bind"]
    assert isinstance(engine, Engine)
    Base.metadata.create_all(engine)
    return database_url, engine


def test_cli_executes_partial_file_and_persists_independent_rows(
    tmp_path: Path,
) -> None:
    database_url, engine = prepared_database(tmp_path, "cli-partial.sqlite3")
    rows = [csv_row(index) for index in range(1, 6)]
    rows[1]["invoice_recurring_amount"] = "99,90"
    rows[3]["external_reference"] = rows[0]["external_reference"]
    file_path = tmp_path / "commercial.csv"
    file_path.write_text(csv_text(rows), encoding="utf-8")
    output = io.StringIO()
    errors = io.StringIO()

    code = main(
        (
            "import-csv",
            str(file_path),
            "--database-url",
            database_url,
            "--verbose",
        ),
        stdout=output,
        stderr=errors,
        environment={},
    )

    assert code == CliExitCode.PARTIAL_FAILURE
    assert errors.getvalue() == ""
    assert "- linhas convertidas: 4" in output.getvalue()
    assert "- sucessos: 3" in output.getvalue()
    assert "- conflitos de negócio: 1" in output.getvalue()
    assert "Linha 3 | csv-row-2 | CSV_ROW_ERROR" in output.getvalue()
    assert "Linha 5 | csv-row-4 | BUSINESS_CONFLICT" in output.getvalue()

    session_factory = build_session_factory(database_url)
    unit_of_work_factory = build_unit_of_work_factory(session_factory)
    with unit_of_work_factory() as unit_of_work:
        for index in (1, 3, 5):
            event_id = f"event-csv-{index}"
            assert unit_of_work.events.get_by_id(event_id) is not None
            assert len(unit_of_work.processing_runs.find_by_event_id(event_id)) == 1
            assert unit_of_work.ledger.find_credit_by_event_id(event_id) is not None
        assert unit_of_work.events.get_by_id("event-csv-2") is None
        assert unit_of_work.events.get_by_id("event-csv-4") is None
    engine.dispose()


def test_cli_reimport_is_successful_without_duplicate_ledger(tmp_path: Path) -> None:
    database_url, engine = prepared_database(tmp_path, "cli-idempotent.sqlite3")
    file_path = tmp_path / "commercial.csv"
    file_path.write_text(csv_text([csv_row(1), csv_row(2)]), encoding="utf-8")

    first_output = io.StringIO()
    second_output = io.StringIO()
    arguments = (
        "import-csv",
        str(file_path),
        "--database-url",
        database_url,
    )
    first = main(arguments, stdout=first_output, stderr=io.StringIO(), environment={})
    second = main(
        arguments,
        stdout=second_output,
        stderr=io.StringIO(),
        environment={},
    )

    assert first == second == CliExitCode.SUCCESS
    assert "- LedgerEntries criadas: 2" in first_output.getvalue()
    assert "- LedgerEntries criadas: 0" in second_output.getvalue()
    session_factory = build_session_factory(database_url)
    unit_of_work_factory = build_unit_of_work_factory(session_factory)
    with unit_of_work_factory() as unit_of_work:
        for index in (1, 2):
            event_id = f"event-csv-{index}"
            assert len(unit_of_work.processing_runs.find_by_event_id(event_id)) == 2
            assert unit_of_work.ledger.find_credit_by_event_id(event_id) is not None
    engine.dispose()


def test_module_entry_point_is_executable() -> None:
    completed = subprocess.run(
        [sys.executable, "-m", "supervisor_ai.cli", "--help"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0
    assert "import-csv" in completed.stdout
