import io
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from supervisor_ai.cli.formatting import format_json_report, format_text_report
from supervisor_ai.cli.main import (
    CliExitCode,
    create_parser,
    main,
    parse_command,
    read_csv_file,
    resolve_database_url,
)
from supervisor_ai.infrastructure.importing import (
    BatchDocumentResult,
    BatchDocumentStatus,
    BatchImportResult,
    BatchStatistics,
    CsvBatchImportResult,
    CsvImportAdapter,
    CsvStructureError,
)
from tests.importing.csv_factories import csv_row, csv_text

NOW = datetime(2026, 7, 22, 14, 0, tzinfo=UTC)


class FakeService:
    def __init__(
        self,
        result: CsvBatchImportResult | None = None,
        error: Exception | None = None,
    ) -> None:
        self.result = result
        self.error = error

    def import_csv(self, content: str) -> CsvBatchImportResult:
        assert content
        if self.error is not None:
            raise self.error
        assert self.result is not None
        return self.result


def batch_result(
    identifier: str,
    status: BatchDocumentStatus = BatchDocumentStatus.SUCCESS,
    *,
    error_type: str | None = None,
) -> BatchDocumentResult:
    success = status is BatchDocumentStatus.SUCCESS
    return BatchDocumentResult(
        document_identifier=identifier,
        processing_status=status,
        started_at=NOW,
        completed_at=NOW + timedelta(seconds=1),
        execution_duration=timedelta(seconds=1),
        processing_run_id=f"run-{identifier}" if success else None,
        commercial_event_id=f"event-{identifier}" if success else None,
        final_status="posted" if success else None,
        ledger_entry_id=f"ledger-{identifier}" if success else None,
        event_persisted=success,
        ledger_persisted=success,
        error_type=error_type,
        error_message="failure detail" if error_type else None,
    )


def report_with_all_categories() -> CsvBatchImportResult:
    rows = [csv_row(index) for index in range(1, 5)]
    rows[1]["invoice_recurring_amount"] = "99,90"
    parsing = CsvImportAdapter().parse(csv_text(rows))
    results = (
        batch_result("csv-row-1"),
        batch_result(
            "csv-row-3",
            BatchDocumentStatus.BUSINESS_CONFLICT,
            error_type="CommercialEventConflict",
        ),
        batch_result(
            "csv-row-4",
            BatchDocumentStatus.TECHNICAL_ERROR,
            error_type="OperationalError",
        ),
    )
    batch = BatchImportResult(
        started_at=NOW,
        completed_at=NOW + timedelta(seconds=3),
        processing_duration=timedelta(seconds=3),
        statistics=BatchStatistics.from_results(results),
        ordered_results=results,
    )
    return CsvBatchImportResult(parsing=parsing, batch=batch)


def test_parses_valid_command_and_flags() -> None:
    command = parse_command(
        (
            "import-csv",
            "data.csv",
            "--database-url",
            "sqlite+pysqlite:///local.sqlite3",
            "--output-format",
            "json",
            "--verbose",
            "--debug",
        ),
        {},
    )
    assert command.file_path == Path("data.csv")
    assert command.output_format == "json"
    assert command.verbose is True
    assert command.debug is True


def test_argparse_rejects_missing_file_and_invalid_output_format() -> None:
    parser = create_parser()
    with pytest.raises(SystemExit) as missing:
        parser.parse_args(("import-csv",))
    with pytest.raises(SystemExit) as invalid:
        parser.parse_args(("import-csv", "data.csv", "--output-format", "xml"))
    assert missing.value.code == invalid.value.code == CliExitCode.USAGE_ERROR


def test_database_argument_precedes_environment_and_empty_is_rejected() -> None:
    environment = {"SUPERVISOR_AI_DATABASE_URL": "sqlite:///environment.sqlite3"}
    assert resolve_database_url("sqlite:///argument.sqlite3", environment) == (
        "sqlite:///argument.sqlite3"
    )
    assert resolve_database_url(None, environment) == "sqlite:///environment.sqlite3"
    with pytest.raises(ValueError, match="must not be empty"):
        resolve_database_url("", environment)
    with pytest.raises(ValueError, match="database URL is required"):
        resolve_database_url(None, {})


def test_reads_utf8_and_utf8_bom_without_modifying_file(tmp_path: Path) -> None:
    normal = tmp_path / "normal.csv"
    bom = tmp_path / "bom.csv"
    normal.write_text("header\nvalue\n", encoding="utf-8")
    bom.write_bytes("header\nvalue\n".encode("utf-8-sig"))
    assert read_csv_file(normal) == "header\nvalue\n"
    assert read_csv_file(bom) == "header\nvalue\n"


def test_file_reader_rejects_missing_directory_and_invalid_encoding(
    tmp_path: Path,
) -> None:
    with pytest.raises(FileNotFoundError):
        read_csv_file(tmp_path / "missing.csv")
    with pytest.raises(IsADirectoryError):
        read_csv_file(tmp_path)
    invalid = tmp_path / "invalid.csv"
    invalid.write_bytes(b"\xff\xfe")
    with pytest.raises(UnicodeDecodeError):
        read_csv_file(invalid)


def test_file_reader_propagates_permission_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    file_path = tmp_path / "data.csv"
    file_path.write_text("header\n", encoding="utf-8")

    def denied(self: Path, *, encoding: str) -> str:
        del self, encoding
        raise PermissionError

    monkeypatch.setattr(Path, "read_text", denied)
    with pytest.raises(PermissionError):
        read_csv_file(file_path)


def test_text_formatter_is_deterministic_and_correlates_physical_lines() -> None:
    report = format_text_report(
        Path("/private/location/data.csv"),
        report_with_all_categories(),
        verbose=True,
    )
    assert "Arquivo: data.csv" in report
    assert "- linhas de dados: 4" in report
    assert "- linhas inválidas: 1" in report
    assert "- conflitos de negócio: 1" in report
    assert "- falhas técnicas: 1" in report
    assert "- duração total: 3.00s" in report
    assert "Linha 3 | csv-row-2 | CSV_ROW_ERROR" in report
    assert "Linha 4 | csv-row-3 | BUSINESS_CONFLICT" in report
    assert "raw_payload" not in report
    assert "/private/location" not in report


def test_json_formatter_has_stable_explicit_projection() -> None:
    serialized = format_json_report(
        Path("data.csv"), report_with_all_categories()
    )
    report = json.loads(serialized)
    assert report["status"] == "partial_failure"
    assert report["file"] == "data.csv"
    assert report["parsing"]["error_rows"] == 1
    assert report["processing"]["business_conflicts"] == 1
    assert report["duration_seconds"] == 3.0
    assert [item["line_number"] for item in report["results"]] == [2, 3, 4, 5]
    assert report["results"][1]["status"] == "csv_row_error"
    assert "value" not in report["results"][1]


def test_main_returns_success_or_partial_failure_and_keeps_json_clean(
    tmp_path: Path,
) -> None:
    file_path = tmp_path / "data.csv"
    file_path.write_text(csv_text([csv_row()]), encoding="utf-8")
    success_result = report_with_all_categories()
    output = io.StringIO()
    errors = io.StringIO()
    code = main(
        (
            "import-csv",
            str(file_path),
            "--database-url",
            "sqlite:///unused.sqlite3",
            "--output-format",
            "json",
        ),
        stdout=output,
        stderr=errors,
        environment={},
        service_builder=lambda database_url: FakeService(success_result),
    )
    assert code == CliExitCode.PARTIAL_FAILURE
    assert json.loads(output.getvalue())["status"] == "partial_failure"
    assert errors.getvalue() == ""


@pytest.mark.parametrize(
    ("service_error", "expected_code", "message"),
    [
        (
            CsvStructureError("required CSV column is missing"),
            CliExitCode.CSV_STRUCTURE_ERROR,
            "CSV structure error",
        ),
        (RuntimeError("secret detail"), CliExitCode.UNEXPECTED_ERROR, "RuntimeError"),
    ],
)
def test_main_categorizes_fatal_service_errors_without_normal_traceback(
    tmp_path: Path,
    service_error: Exception,
    expected_code: CliExitCode,
    message: str,
) -> None:
    file_path = tmp_path / "data.csv"
    file_path.write_text("content", encoding="utf-8")
    output = io.StringIO()
    errors = io.StringIO()
    code = main(
        ("import-csv", str(file_path), "--database-url", "sqlite:///unused"),
        stdout=output,
        stderr=errors,
        environment={},
        service_builder=lambda database_url: FakeService(error=service_error),
    )
    assert code == expected_code
    assert output.getvalue() == ""
    assert message in errors.getvalue()
    assert "Traceback" not in errors.getvalue()
    assert "secret detail" not in errors.getvalue()


def test_main_reports_configuration_file_and_initialization_errors(
    tmp_path: Path,
) -> None:
    output = io.StringIO()
    errors = io.StringIO()
    missing_config = main(
        ("import-csv", "data.csv"),
        stdout=output,
        stderr=errors,
        environment={},
    )
    assert missing_config == CliExitCode.CONFIGURATION_ERROR

    errors = io.StringIO()
    missing_file = main(
        ("import-csv", "missing.csv", "--database-url", "sqlite:///unused"),
        stdout=io.StringIO(),
        stderr=errors,
        environment={},
    )
    assert missing_file == CliExitCode.FILE_ERROR

    file_path = tmp_path / "data.csv"
    file_path.write_text("content", encoding="utf-8")
    errors = io.StringIO()

    def fail_initialization(database_url: str) -> FakeService:
        del database_url
        raise RuntimeError("database password")

    initialization = main(
        ("import-csv", str(file_path), "--database-url", "postgresql://secret"),
        stdout=io.StringIO(),
        stderr=errors,
        environment={},
        service_builder=fail_initialization,
    )
    assert initialization == CliExitCode.CONFIGURATION_ERROR
    assert "database password" not in errors.getvalue()
