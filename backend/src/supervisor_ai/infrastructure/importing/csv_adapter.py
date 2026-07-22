import csv
import io
import json
import re
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum
from typing import Protocol
from uuid import UUID

from supervisor_ai.infrastructure.importing.batch import (
    BatchDocument,
    BatchImportResult,
)
from supervisor_ai.infrastructure.importing.errors import ImportDocumentError
from supervisor_ai.infrastructure.importing.parser import parse_json_text
from supervisor_ai.rules_engine import InvoicePaymentStatus, NonLoyaltyAdditionalType

DECIMAL_PATTERN = re.compile(r"(?:0|[1-9][0-9]*)(?:\.[0-9]+)?\Z")
INTEGER_PATTERN = re.compile(r"(?:0|[1-9][0-9]*)\Z")

EVENT_COLUMNS = (
    "document_identifier",
    "event_id",
    "external_reference",
    "source",
    "event_occurred_at",
    "event_received_at",
    "raw_payload",
    "evaluation_id",
    "subject_id",
    "evaluation_observed_at",
    "rules_engine_version",
)
CONTRACTUAL_COLUMNS = (
    "previous_speed",
    "current_speed",
    "previous_plan_modality",
    "current_plan_modality",
    "previous_mesh_enabled",
    "current_mesh_enabled",
    "previous_additionals",
    "current_additionals",
    "previous_recurring_value",
    "current_recurring_value",
)
OPERATIONAL_COLUMNS = (
    "ticket_id",
    "support_agent_id",
    "ticket_author_id",
    "duplicate_author_detected",
    "ticket_linked_to_plan_change",
    "change_marked_administrative",
    "change_marked_corrective",
    "conflicting_authorship_evidence_found",
)
PAYMENT_COLUMNS = (
    "payment_evaluated_at",
    "invoice_id",
    "invoice_due_date",
    "invoice_paid_at",
    "invoice_status",
    "invoice_recurring_amount",
    "expected_recurring_amount",
    "invoice_linked_to_event",
    "is_first_new_value_invoice",
    "first_invoice_candidate_count",
    "already_validated_event_ids",
    "financial_reference_ids",
    "has_link_conflict",
    "has_duplicate_invoice_event_link",
    "has_inconsistent_financial_input",
)
REMUNERATION_COLUMNS = (
    "payment_validation_reference",
    "previous_remuneration_recurring_amount",
    "new_remuneration_recurring_amount",
    "full_new_plan_amount",
    "additional_type",
    "renews_loyalty",
    "commercial_reference_ids",
    "calculation_reference_ids",
    "has_commercial_classification_conflict",
    "has_inconsistent_remuneration_input",
)
POSTING_COLUMNS = (
    "beneficiary_id",
    "posted_at",
    "posting_reference",
    "source_reference_ids",
    "remuneration_calculation_reference",
    "has_ledger_reference_conflict",
    "has_inconsistent_posting_input",
)
FINANCIAL_COLUMNS = (
    "financial_snapshot_present",
    *PAYMENT_COLUMNS,
    *REMUNERATION_COLUMNS,
    *POSTING_COLUMNS,
)
CSV_COLUMNS = (
    *EVENT_COLUMNS,
    *CONTRACTUAL_COLUMNS,
    *OPERATIONAL_COLUMNS,
    *FINANCIAL_COLUMNS,
)


class CsvStructureError(ImportDocumentError):
    """O arquivo CSV não possui uma estrutura global processável."""


class CsvRowErrorCategory(StrEnum):
    CSV_ROW_ERROR = "csv_row_error"


@dataclass(frozen=True, slots=True)
class CsvColumnSchema:
    columns: tuple[str, ...] = CSV_COLUMNS

    def __post_init__(self) -> None:
        if not self.columns or len(self.columns) != len(set(self.columns)):
            raise ValueError("CSV schema columns must be non-empty and unique")


@dataclass(frozen=True, slots=True)
class CsvRowError:
    line_number: int
    column: str
    value: str
    category: CsvRowErrorCategory
    message: str


@dataclass(frozen=True, slots=True)
class CsvRowResult:
    line_number: int
    document_identifier: str | None
    document: BatchDocument[str] | None
    errors: tuple[CsvRowError, ...]

    def __post_init__(self) -> None:
        if self.line_number < 2:
            raise ValueError("data row line number must be at least 2")
        if (self.document is None) == (not self.errors):
            raise ValueError("row result must contain either a document or errors")


@dataclass(frozen=True, slots=True)
class CsvParseStatistics:
    total_data_rows: int
    converted_rows: int
    error_rows: int
    ignored_empty_rows: int


@dataclass(frozen=True, slots=True)
class CsvParseResult:
    rows: tuple[CsvRowResult, ...]
    statistics: CsvParseStatistics

    def __post_init__(self) -> None:
        converted = sum(row.document is not None for row in self.rows)
        errors = len(self.rows) - converted
        if self.statistics.converted_rows != converted:
            raise ValueError("converted row statistics do not match rows")
        if self.statistics.error_rows != errors:
            raise ValueError("error row statistics do not match rows")
        if self.statistics.total_data_rows != len(self.rows):
            raise ValueError("total row statistics do not match rows")

    @property
    def documents(self) -> tuple[BatchDocument[str], ...]:
        return tuple(row.document for row in self.rows if row.document is not None)


@dataclass(frozen=True, slots=True)
class CsvBatchImportResult:
    parsing: CsvParseResult
    batch: BatchImportResult


class StringBatchProcessor(Protocol):
    def process(
        self, documents: tuple[BatchDocument[str], ...]
    ) -> BatchImportResult: ...


class CsvImportAdapter:
    def __init__(self, schema: CsvColumnSchema | None = None) -> None:
        self._schema = schema or CsvColumnSchema()

    def parse(self, content: str) -> CsvParseResult:
        if not content:
            raise CsvStructureError("CSV header is missing")
        reader = csv.reader(io.StringIO(content), strict=True)
        try:
            header = next(reader)
        except StopIteration as error:
            raise CsvStructureError("CSV header is missing") from error
        except csv.Error as error:
            raise CsvStructureError(f"invalid CSV structure: {error}") from error
        self._validate_header(header)

        results: list[CsvRowResult] = []
        ignored_empty_rows = 0
        try:
            for values in reader:
                line_number = reader.line_num
                if not values or all(value == "" for value in values):
                    ignored_empty_rows += 1
                    continue
                results.append(self._parse_row(line_number, header, values))
        except csv.Error as error:
            raise CsvStructureError(
                f"invalid CSV structure at line {reader.line_num}: {error}"
            ) from error

        rows = _reject_duplicate_identifiers(tuple(results))
        return CsvParseResult(
            rows=rows,
            statistics=CsvParseStatistics(
                total_data_rows=len(rows),
                converted_rows=sum(row.document is not None for row in rows),
                error_rows=sum(row.document is None for row in rows),
                ignored_empty_rows=ignored_empty_rows,
            ),
        )

    def _validate_header(self, header: list[str]) -> None:
        if not header or all(not value for value in header):
            raise CsvStructureError("CSV header is missing")
        duplicates = sorted({name for name in header if header.count(name) > 1})
        if duplicates:
            raise CsvStructureError(f"duplicate CSV column {duplicates[0]!r}")
        expected = set(self._schema.columns)
        actual = set(header)
        unknown = sorted(actual - expected)
        if unknown:
            raise CsvStructureError(f"unknown CSV column {unknown[0]!r}")
        missing = sorted(expected - actual)
        if missing:
            raise CsvStructureError(f"required CSV column {missing[0]!r} is missing")

    def _parse_row(
        self, line_number: int, header: list[str], values: list[str]
    ) -> CsvRowResult:
        if len(values) != len(header):
            message = (
                "row has extra columns"
                if len(values) > len(header)
                else "row has missing columns"
            )
            identifier = None
            identifier_index = header.index("document_identifier")
            if identifier_index < len(values):
                identifier = values[identifier_index] or None
            return _failed_row(
                line_number,
                "$row",
                "",
                message,
                document_identifier=identifier,
            )
        row = dict(zip(header, values, strict=True))
        identifier = row["document_identifier"] or None
        try:
            document = _build_document(row)
        except _CsvCellError as error:
            return CsvRowResult(
                line_number=line_number,
                document_identifier=identifier,
                document=None,
                errors=(
                    CsvRowError(
                        line_number=line_number,
                        column=error.column,
                        value=error.value,
                        category=CsvRowErrorCategory.CSV_ROW_ERROR,
                        message=error.message,
                    ),
                ),
            )
        return CsvRowResult(line_number, identifier, document, ())


class CsvImportService:
    def __init__(
        self,
        *,
        adapter: CsvImportAdapter,
        batch_processor: StringBatchProcessor,
    ) -> None:
        self._adapter = adapter
        self._batch_processor = batch_processor

    def import_csv(self, content: str) -> CsvBatchImportResult:
        parsing = self._adapter.parse(content)
        batch = self._batch_processor.process(parsing.documents)
        return CsvBatchImportResult(parsing=parsing, batch=batch)


class _CsvCellError(Exception):
    def __init__(self, column: str, value: str, message: str) -> None:
        self.column = column
        self.value = value
        self.message = message
        super().__init__(message)


def _build_document(row: dict[str, str]) -> BatchDocument[str]:
    required = (
        *EVENT_COLUMNS,
        *CONTRACTUAL_COLUMNS,
        *OPERATIONAL_COLUMNS,
        "financial_snapshot_present",
    )
    for column in required:
        _required(row, column)
    _uuid(row, "evaluation_id")
    for column in (
        "event_occurred_at",
        "event_received_at",
        "evaluation_observed_at",
    ):
        _timestamp(row, column)

    observed_at = row["evaluation_observed_at"]
    evidence = _contractual_evidence(row, observed_at)
    evidence.extend(_operational_evidence(row, observed_at))
    document: dict[str, object] = {
        "event": {
            "id": row["event_id"],
            "external_reference": row["external_reference"],
            "source": row["source"],
            "occurred_at": row["event_occurred_at"],
            "received_at": row["event_received_at"],
            "raw_payload": _json_object(row, "raw_payload"),
        },
        "evaluation": {
            "evaluation_id": row["evaluation_id"],
            "subject_id": row["subject_id"],
            "observed_at": observed_at,
            "evidence": evidence,
        },
        "rules_engine_version": row["rules_engine_version"],
    }
    snapshot_present = _boolean(row, "financial_snapshot_present")
    if snapshot_present:
        document["financial_snapshot"] = _financial_snapshot(row)
    elif any(row[column] for column in FINANCIAL_COLUMNS[1:]):
        raise _CsvCellError(
            "financial_snapshot_present",
            row["financial_snapshot_present"],
            "financial fields require financial_snapshot_present=true",
        )
    return BatchDocument(
        identifier=row["document_identifier"],
        document=json.dumps(document, ensure_ascii=False, separators=(",", ":")),
    )


def _contractual_evidence(
    row: dict[str, str], observed_at: str
) -> list[dict[str, object]]:
    values: tuple[tuple[str, object], ...] = (
        ("previous_speed", _integer(row, "previous_speed")),
        ("current_speed", _integer(row, "current_speed")),
        ("previous_plan_modality", row["previous_plan_modality"]),
        ("current_plan_modality", row["current_plan_modality"]),
        ("previous_mesh_enabled", _boolean(row, "previous_mesh_enabled")),
        ("current_mesh_enabled", _boolean(row, "current_mesh_enabled")),
        ("previous_additionals", _json_string_array(row, "previous_additionals")),
        ("current_additionals", _json_string_array(row, "current_additionals")),
        ("previous_recurring_value", _decimal(row, "previous_recurring_value")),
        ("current_recurring_value", _decimal(row, "current_recurring_value")),
    )
    return [
        _evidence(f"csv.{name}", name, value, observed_at) for name, value in values
    ]


def _operational_evidence(
    row: dict[str, str], observed_at: str
) -> list[dict[str, object]]:
    values: tuple[tuple[str, str, object], ...] = (
        ("ticket", "ticket_found", row["ticket_id"]),
        ("support", "ticket_opened_by_support", row["support_agent_id"]),
        ("author", "ticket_author_identified", row["ticket_author_id"]),
        (
            "duplicate",
            "duplicate_author_detected"
            if _boolean(row, "duplicate_author_detected")
            else "duplicate_author_not_detected",
            _boolean(row, "duplicate_author_detected"),
        ),
        (
            "purpose",
            "ticket_linked_to_plan_change"
            if _boolean(row, "ticket_linked_to_plan_change")
            else "ticket_not_linked_to_plan_change",
            _boolean(row, "ticket_linked_to_plan_change"),
        ),
        (
            "administrative",
            "change_marked_administrative"
            if _boolean(row, "change_marked_administrative")
            else "change_not_marked_administrative",
            _boolean(row, "change_marked_administrative"),
        ),
        (
            "corrective",
            "change_marked_corrective"
            if _boolean(row, "change_marked_corrective")
            else "change_not_marked_corrective",
            _boolean(row, "change_marked_corrective"),
        ),
        (
            "authorship",
            "conflicting_authorship_evidence_found"
            if _boolean(row, "conflicting_authorship_evidence_found")
            else "conflicting_authorship_evidence_not_found",
            _boolean(row, "conflicting_authorship_evidence_found"),
        ),
    )
    return [
        _evidence(f"csv.{key}", name, value, observed_at) for key, name, value in values
    ]


def _financial_snapshot(row: dict[str, str]) -> dict[str, object]:
    for column in FINANCIAL_COLUMNS[1:]:
        if column not in {
            "invoice_id",
            "invoice_due_date",
            "invoice_paid_at",
            "invoice_status",
            "invoice_recurring_amount",
            "expected_recurring_amount",
            "additional_type",
            "beneficiary_id",
            "posted_at",
            "posting_reference",
            "remuneration_calculation_reference",
            "previous_remuneration_recurring_amount",
            "new_remuneration_recurring_amount",
            "full_new_plan_amount",
        }:
            _required(row, column)
    for column in ("payment_evaluated_at",):
        _timestamp(row, column)
    for column in ("invoice_paid_at", "posted_at"):
        if row[column]:
            _timestamp(row, column)
    if row["invoice_due_date"]:
        _date(row, "invoice_due_date")
    invoice_status = _optional_enum(row, "invoice_status", InvoicePaymentStatus)
    additional_type = _optional_enum(row, "additional_type", NonLoyaltyAdditionalType)
    return {
        "payment": {
            "evaluated_at": row["payment_evaluated_at"],
            "invoice_id": _optional(row, "invoice_id"),
            "invoice_due_date": _optional(row, "invoice_due_date"),
            "invoice_paid_at": _optional(row, "invoice_paid_at"),
            "invoice_status": None if invoice_status is None else invoice_status.value,
            "invoice_recurring_amount": _optional_decimal(
                row, "invoice_recurring_amount"
            ),
            "expected_recurring_amount": _optional_decimal(
                row, "expected_recurring_amount"
            ),
            "invoice_linked_to_event": _optional_boolean(
                row, "invoice_linked_to_event"
            ),
            "is_first_new_value_invoice": _optional_boolean(
                row, "is_first_new_value_invoice"
            ),
            "first_invoice_candidate_count": _optional_integer(
                row, "first_invoice_candidate_count"
            ),
            "already_validated_event_ids": _json_string_array(
                row, "already_validated_event_ids"
            ),
            "financial_reference_ids": _json_string_array(
                row, "financial_reference_ids"
            ),
            "has_link_conflict": _boolean(row, "has_link_conflict"),
            "has_duplicate_invoice_event_link": _boolean(
                row, "has_duplicate_invoice_event_link"
            ),
            "has_inconsistent_financial_input": _boolean(
                row, "has_inconsistent_financial_input"
            ),
        },
        "remuneration": {
            "payment_validation_reference": row["payment_validation_reference"],
            "previous_recurring_amount": _optional_decimal(
                row, "previous_remuneration_recurring_amount"
            ),
            "new_recurring_amount": _optional_decimal(
                row, "new_remuneration_recurring_amount"
            ),
            "full_new_plan_amount": _optional_decimal(row, "full_new_plan_amount"),
            "additional_type": None
            if additional_type is None
            else additional_type.value,
            "renews_loyalty": _optional_boolean(row, "renews_loyalty"),
            "commercial_reference_ids": _json_string_array(
                row, "commercial_reference_ids"
            ),
            "calculation_reference_ids": _json_string_array(
                row, "calculation_reference_ids"
            ),
            "has_commercial_classification_conflict": _boolean(
                row, "has_commercial_classification_conflict"
            ),
            "has_inconsistent_input": _boolean(
                row, "has_inconsistent_remuneration_input"
            ),
        },
        "posting": {
            "beneficiary_id": _optional(row, "beneficiary_id"),
            "posted_at": _optional(row, "posted_at"),
            "posting_reference": _optional(row, "posting_reference"),
            "source_reference_ids": _json_string_array(row, "source_reference_ids"),
            "remuneration_calculation_reference": _optional(
                row, "remuneration_calculation_reference"
            ),
            "has_ledger_reference_conflict": _boolean(
                row, "has_ledger_reference_conflict"
            ),
            "has_inconsistent_input": _boolean(row, "has_inconsistent_posting_input"),
        },
    }


def _evidence(
    identifier: str, name: str, value: object, observed_at: str
) -> dict[str, object]:
    return {"id": identifier, "name": name, "value": value, "observed_at": observed_at}


def _required(row: dict[str, str], column: str) -> str:
    value = row[column]
    if not value:
        raise _CsvCellError(column, value, "required field must not be empty")
    return value


def _optional(row: dict[str, str], column: str) -> str | None:
    return row[column] or None


def _boolean(row: dict[str, str], column: str) -> bool:
    value = _required(row, column)
    if value == "true":
        return True
    if value == "false":
        return False
    raise _CsvCellError(column, value, "expected canonical boolean 'true' or 'false'")


def _optional_boolean(row: dict[str, str], column: str) -> bool | None:
    return None if not row[column] else _boolean(row, column)


def _integer(row: dict[str, str], column: str) -> int:
    value = _required(row, column)
    if INTEGER_PATTERN.fullmatch(value) is None:
        raise _CsvCellError(column, value, "expected non-negative integer")
    return int(value)


def _optional_integer(row: dict[str, str], column: str) -> int | None:
    return None if not row[column] else _integer(row, column)


def _decimal(row: dict[str, str], column: str) -> str:
    value = _required(row, column)
    if DECIMAL_PATTERN.fullmatch(value) is None:
        raise _CsvCellError(
            column, value, "expected canonical decimal with point separator"
        )
    return value


def _optional_decimal(row: dict[str, str], column: str) -> str | None:
    return None if not row[column] else _decimal(row, column)


def _timestamp(row: dict[str, str], column: str) -> str:
    value = _required(row, column)
    candidate = f"{value[:-1]}+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError as error:
        raise _CsvCellError(column, value, "invalid ISO 8601 timestamp") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise _CsvCellError(column, value, "timezone offset is required")
    return value


def _uuid(row: dict[str, str], column: str) -> str:
    value = _required(row, column)
    try:
        UUID(value)
    except ValueError as error:
        raise _CsvCellError(column, value, "invalid UUID") from error
    return value


def _date(row: dict[str, str], column: str) -> str:
    value = _required(row, column)
    try:
        date.fromisoformat(value)
    except ValueError as error:
        raise _CsvCellError(column, value, "invalid ISO 8601 date") from error
    return value


def _json_object(row: dict[str, str], column: str) -> dict[str, object]:
    value = _required(row, column)
    try:
        parsed = parse_json_text(value)
    except ImportDocumentError as error:
        raise _CsvCellError(column, value, str(error)) from error
    if not isinstance(parsed, dict):
        raise _CsvCellError(column, value, "expected JSON object")
    return parsed


def _json_string_array(row: dict[str, str], column: str) -> list[str]:
    value = _required(row, column)
    try:
        parsed = parse_json_text(value)
    except ImportDocumentError as error:
        raise _CsvCellError(column, value, str(error)) from error
    if not isinstance(parsed, list) or any(type(item) is not str for item in parsed):
        raise _CsvCellError(column, value, "expected JSON array of strings")
    return parsed


def _optional_enum[EnumT](
    row: dict[str, str], column: str, enum_type: type[EnumT]
) -> EnumT | None:
    value = row[column]
    if not value:
        return None
    try:
        return enum_type(value)
    except ValueError as error:
        raise _CsvCellError(column, value, "unknown enum value") from error


def _failed_row(
    line_number: int,
    column: str,
    value: str,
    message: str,
    *,
    document_identifier: str | None = None,
) -> CsvRowResult:
    return CsvRowResult(
        line_number=line_number,
        document_identifier=document_identifier,
        document=None,
        errors=(
            CsvRowError(
                line_number=line_number,
                column=column,
                value=value,
                category=CsvRowErrorCategory.CSV_ROW_ERROR,
                message=message,
            ),
        ),
    )


def _reject_duplicate_identifiers(
    rows: tuple[CsvRowResult, ...],
) -> tuple[CsvRowResult, ...]:
    counts = Counter(
        row.document_identifier
        for row in rows
        if row.document is not None and row.document_identifier is not None
    )
    duplicates = {identifier for identifier, count in counts.items() if count > 1}
    if not duplicates:
        return rows
    return tuple(
        _failed_row(
            row.line_number,
            "document_identifier",
            row.document_identifier or "",
            "document identifier is duplicated in this CSV file",
            document_identifier=row.document_identifier,
        )
        if row.document is not None and row.document_identifier in duplicates
        else row
        for row in rows
    )
