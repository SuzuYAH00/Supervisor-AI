import csv
import io
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Protocol

from supervisor_ai.application.use_cases.import_csat_evaluations import (
    CsatEvaluationInput,
    ImportCsatEvaluationsCommand,
    ImportCsatEvaluationsResult,
)

CSAT_CSV_COLUMNS = (
    "evaluation_id",
    "external_reference",
    "source",
    "collaborator_id",
    "channel",
    "score",
    "evaluated_at",
)
DECIMAL_PATTERN = re.compile(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]{1,6})?\Z")


class CsatCsvStructureError(ValueError):
    """O CSV não possui o contrato estrutural de CSAT."""


class CsatCsvValidationError(ValueError):
    """Uma linha não representa uma avaliação CSAT factual válida."""


class CsatImporter(Protocol):
    def execute(
        self, command: ImportCsatEvaluationsCommand
    ) -> ImportCsatEvaluationsResult: ...


class CsatCsvImportService:
    def __init__(self, importer: CsatImporter) -> None:
        self._importer = importer

    def import_csv(self, content: str) -> ImportCsatEvaluationsResult:
        return self._importer.execute(
            ImportCsatEvaluationsCommand(_parse_csat_csv(content))
        )


def _parse_csat_csv(content: str) -> tuple[CsatEvaluationInput, ...]:
    if not content:
        raise CsatCsvStructureError("CSV header is missing")
    reader = csv.DictReader(io.StringIO(content), strict=True)
    _validate_header(reader.fieldnames)
    evaluations: list[CsatEvaluationInput] = []
    seen_ids: set[str] = set()
    seen_references: set[tuple[str, str]] = set()
    try:
        for row in reader:
            line_number = reader.line_num
            if None in row:
                raise CsatCsvValidationError(
                    f"line {line_number} has extra columns"
                )
            evaluation = _parse_row(row, line_number)
            source_reference = (
                evaluation.source,
                evaluation.external_reference,
            )
            if evaluation.evaluation_id in seen_ids:
                raise CsatCsvValidationError(
                    f"line {line_number} repeats evaluation_id"
                )
            if source_reference in seen_references:
                raise CsatCsvValidationError(
                    f"line {line_number} repeats source reference"
                )
            seen_ids.add(evaluation.evaluation_id)
            seen_references.add(source_reference)
            evaluations.append(evaluation)
    except csv.Error as error:
        raise CsatCsvStructureError("CSV structure is invalid") from error
    return tuple(evaluations)


def _validate_header(fieldnames: list[str] | None) -> None:
    if fieldnames is None:
        raise CsatCsvStructureError("CSV header is missing")
    if len(fieldnames) != len(set(fieldnames)):
        raise CsatCsvStructureError("CSV header contains duplicate columns")
    if set(fieldnames) != set(CSAT_CSV_COLUMNS):
        raise CsatCsvStructureError("CSV header does not match CSAT contract")


def _parse_row(
    row: dict[str | None, str | None], line_number: int
) -> CsatEvaluationInput:
    evaluation_id = _required(row, "evaluation_id", line_number, 128)
    external_reference = _required(row, "external_reference", line_number, 255)
    source = _required(row, "source", line_number, 100)
    collaborator_id = _required(row, "collaborator_id", line_number, 128)
    channel_value = row.get("channel")
    channel = None if channel_value == "" else channel_value
    if channel is not None:
        _validate_text(channel, "channel", line_number, 100)
    score_text = _required(row, "score", line_number, 30)
    if DECIMAL_PATTERN.fullmatch(score_text) is None:
        raise CsatCsvValidationError(f"line {line_number} has invalid score")
    try:
        score = Decimal(score_text)
    except InvalidOperation as error:
        raise CsatCsvValidationError(
            f"line {line_number} has invalid score"
        ) from error
    evaluated_at_text = _required(row, "evaluated_at", line_number, 64)
    try:
        evaluated_at = datetime.fromisoformat(
            evaluated_at_text.replace("Z", "+00:00")
        )
    except ValueError as error:
        raise CsatCsvValidationError(
            f"line {line_number} has invalid evaluated_at"
        ) from error
    if evaluated_at.tzinfo is None or evaluated_at.utcoffset() is None:
        raise CsatCsvValidationError(
            f"line {line_number} evaluated_at must include timezone"
        )
    try:
        return CsatEvaluationInput(
            evaluation_id=evaluation_id,
            external_reference=external_reference,
            source=source,
            collaborator_id=collaborator_id,
            channel=channel,
            score=score,
            evaluated_at=evaluated_at,
        )
    except ValueError as error:
        raise CsatCsvValidationError(
            f"line {line_number} contains invalid values"
        ) from error


def _required(
    row: dict[str | None, str | None],
    field: str,
    line_number: int,
    maximum_length: int,
) -> str:
    value = row.get(field)
    if value is None:
        raise CsatCsvValidationError(f"line {line_number} is missing {field}")
    _validate_text(value, field, line_number, maximum_length)
    return value


def _validate_text(
    value: str, field: str, line_number: int, maximum_length: int
) -> None:
    if not value.strip() or value != value.strip() or len(value) > maximum_length:
        raise CsatCsvValidationError(f"line {line_number} has invalid {field}")
