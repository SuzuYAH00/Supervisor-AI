import csv
import io
import json
from dataclasses import FrozenInstanceError

import pytest

from supervisor_ai.infrastructure.importing import (
    CSV_COLUMNS,
    CsvColumnSchema,
    CsvImportAdapter,
    CsvRowErrorCategory,
    CsvStructureError,
)
from supervisor_ai.infrastructure.importing.parser import parse_json_text
from tests.importing.csv_factories import csv_row, csv_text


def test_parses_complete_row_and_preserves_line_correlation() -> None:
    parsed = CsvImportAdapter().parse(csv_text([csv_row()]))

    assert parsed.statistics.total_data_rows == 1
    assert parsed.statistics.converted_rows == 1
    assert parsed.rows[0].line_number == 2
    assert parsed.rows[0].document_identifier == "csv-row-1"
    assert parsed.documents[0].identifier == "csv-row-1"
    document = parse_json_text(parsed.documents[0].document)
    assert isinstance(document, dict)
    evaluation = document["evaluation"]
    assert isinstance(evaluation, dict)
    evidence = evaluation["evidence"]
    assert isinstance(evidence, list)
    recurring = next(
        item for item in evidence if item["name"] == "previous_recurring_value"
    )
    assert recurring["value"] == "89.90"
    assert type(recurring["value"]) is str


def test_contracts_are_immutable_and_statistics_are_validated() -> None:
    parsed = CsvImportAdapter().parse(csv_text([csv_row()]))
    with pytest.raises(FrozenInstanceError):
        parsed.rows = ()
    with pytest.raises(ValueError, match="unique"):
        CsvColumnSchema(("duplicate", "duplicate"))


@pytest.mark.parametrize(
    ("content", "message"),
    [
        ("", "header is missing"),
        ("\n", "header is missing"),
        ("unknown\nvalue\n", "unknown CSV column"),
    ],
)
def test_rejects_missing_or_unknown_global_header(
    content: str, message: str
) -> None:
    with pytest.raises(CsvStructureError, match=message):
        CsvImportAdapter().parse(content)


def test_rejects_missing_column_duplicate_header_and_forbidden_columns() -> None:
    missing = tuple(column for column in CSV_COLUMNS if column != "event_id")
    with pytest.raises(CsvStructureError, match="event_id.*missing"):
        CsvImportAdapter().parse(csv_text([], columns=missing))

    duplicate = (*CSV_COLUMNS, "event_id")
    with pytest.raises(CsvStructureError, match="duplicate CSV column 'event_id'"):
        CsvImportAdapter().parse(csv_text([], columns=duplicate))

    for forbidden in (
        "commercial_event_type",
        "commercial_classification",
        "operational_decision",
        "eligibility_status",
        "calculated_remuneration_amount",
        "ledger_entry_id",
    ):
        with pytest.raises(CsvStructureError, match="unknown CSV column"):
            CsvImportAdapter().parse(csv_text([], columns=(*CSV_COLUMNS, forbidden)))


def test_header_order_is_irrelevant_and_header_only_is_valid() -> None:
    reversed_columns = tuple(reversed(CSV_COLUMNS))
    parsed = CsvImportAdapter().parse(
        csv_text([csv_row()], columns=reversed_columns)
    )
    empty = CsvImportAdapter().parse(csv_text([]))
    assert parsed.statistics.converted_rows == 1
    assert empty.statistics.total_data_rows == 0
    assert empty.documents == ()


@pytest.mark.parametrize(
    ("column", "invalid", "message"),
    [
        ("event_id", "", "required field"),
        ("invoice_recurring_amount", "99,90", "canonical decimal"),
        ("invoice_recurring_amount", "9.9.0", "canonical decimal"),
        ("invoice_linked_to_event", "yes", "canonical boolean"),
        ("event_occurred_at", "2026-07-22T12:00:00", "timezone offset"),
        ("invoice_status", "settled", "unknown enum"),
        ("raw_payload", "[]", "expected JSON object"),
    ],
)
def test_records_deterministic_cell_errors_and_does_not_emit_document(
    column: str, invalid: str, message: str
) -> None:
    row = csv_row()
    row[column] = invalid
    parsed = CsvImportAdapter().parse(csv_text([row]))
    error = parsed.rows[0].errors[0]
    assert parsed.documents == ()
    assert error.line_number == 2
    assert error.column == column
    assert error.value == invalid
    assert error.category is CsvRowErrorCategory.CSV_ROW_ERROR
    assert message in error.message


def test_optional_financial_snapshot_can_be_absent_without_filling_defaults() -> None:
    row = csv_row()
    row["financial_snapshot_present"] = "false"
    for column in CSV_COLUMNS[CSV_COLUMNS.index("payment_evaluated_at") :]:
        row[column] = ""
    parsed = CsvImportAdapter().parse(csv_text([row]))
    document = json.loads(parsed.documents[0].document)
    assert "financial_snapshot" not in document


def test_ignores_physical_empty_lines_and_keeps_following_line_number() -> None:
    content = csv_text([csv_row()]) + "\n" + csv_text([csv_row(2)]).split("\n", 1)[1]
    parsed = CsvImportAdapter().parse(content)
    assert parsed.statistics.ignored_empty_rows == 1
    assert tuple(row.line_number for row in parsed.rows) == (2, 4)


def test_extra_and_missing_cells_are_row_errors() -> None:
    valid = csv_text([csv_row()])
    lines = valid.splitlines()
    extra = f"{lines[1]},extra"
    stream = io.StringIO(newline="")
    csv.writer(stream, lineterminator="\n").writerow(
        next(csv.reader([lines[1]]))[:-1]
    )
    missing = stream.getvalue().rstrip("\n")
    parsed = CsvImportAdapter().parse(f"{lines[0]}\n{extra}\n{missing}\n")
    assert parsed.statistics.error_rows == 2
    assert parsed.rows[0].errors[0].message == "row has extra columns"
    assert parsed.rows[1].errors[0].message == "row has missing columns"


def test_multiple_row_errors_do_not_stop_later_valid_rows() -> None:
    first = csv_row(1)
    first["previous_speed"] = ""
    second = csv_row(2)
    second["renews_loyalty"] = "1"
    third = csv_row(3)
    parsed = CsvImportAdapter().parse(csv_text([first, second, third]))
    assert parsed.statistics.error_rows == 2
    assert parsed.statistics.converted_rows == 1
    assert parsed.documents[0].identifier == "csv-row-3"
