from dataclasses import dataclass
from datetime import date, datetime

from supervisor_ai.application.persistence import (
    ProcessingRunCursorPosition,
    ProcessingRunListRecord,
)
from supervisor_ai.application.ports import UnitOfWorkFactory

DEFAULT_PROCESSING_RUNS_LIMIT = 50
MAX_PROCESSING_RUNS_LIMIT = 100
MAX_SOURCE_LENGTH = 100
MAX_EXTERNAL_REFERENCE_LENGTH = 255
MAX_FINAL_STATUS_LENGTH = 100
MAX_RULES_ENGINE_VERSION_LENGTH = 100


@dataclass(frozen=True, slots=True)
class ListProcessingRunsQuery:
    source: str | None = None
    external_reference: str | None = None
    final_status: str | None = None
    rules_engine_version: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    limit: int = DEFAULT_PROCESSING_RUNS_LIMIT
    after: ProcessingRunCursorPosition | None = None

    def __post_init__(self) -> None:
        _validate_optional_text(self.source, "source", MAX_SOURCE_LENGTH)
        _validate_optional_text(
            self.external_reference,
            "external_reference",
            MAX_EXTERNAL_REFERENCE_LENGTH,
        )
        _validate_optional_text(
            self.final_status,
            "final_status",
            MAX_FINAL_STATUS_LENGTH,
        )
        _validate_optional_text(
            self.rules_engine_version,
            "rules_engine_version",
            MAX_RULES_ENGINE_VERSION_LENGTH,
        )
        if (
            self.start_date is not None
            and self.end_date is not None
            and self.start_date > self.end_date
        ):
            raise ValueError("start_date must not be after end_date")
        if not 1 <= self.limit <= MAX_PROCESSING_RUNS_LIMIT:
            raise ValueError(
                f"limit must be between 1 and {MAX_PROCESSING_RUNS_LIMIT}"
            )


@dataclass(frozen=True, slots=True)
class ProcessingRunListItem:
    processing_run_id: str
    event_id: str
    source: str
    external_reference: str
    started_at: datetime
    completed_at: datetime
    final_status: str
    rules_engine_version: str


@dataclass(frozen=True, slots=True)
class ListProcessingRunsResult:
    items: tuple[ProcessingRunListItem, ...]
    next_cursor_position: ProcessingRunCursorPosition | None


class ListProcessingRunsUseCase:
    """Lista execuções persistidas por keyset sem carregar JSONs internos."""

    def __init__(self, unit_of_work_factory: UnitOfWorkFactory) -> None:
        self._unit_of_work_factory = unit_of_work_factory

    def execute(self, query: ListProcessingRunsQuery) -> ListProcessingRunsResult:
        with self._unit_of_work_factory() as unit_of_work:
            records = unit_of_work.processing_runs.search(
                source=query.source,
                external_reference=query.external_reference,
                final_status=query.final_status,
                rules_engine_version=query.rules_engine_version,
                start_date=query.start_date,
                end_date=query.end_date,
                after=query.after,
                limit=query.limit + 1,
            )
        has_more = len(records) > query.limit
        page = records[: query.limit]
        return ListProcessingRunsResult(
            items=tuple(_list_item(record) for record in page),
            next_cursor_position=(
                ProcessingRunCursorPosition(
                    started_at=page[-1].started_at,
                    processing_run_id=page[-1].processing_run_id,
                )
                if has_more
                else None
            ),
        )


def _validate_optional_text(
    value: str | None,
    field_name: str,
    maximum_length: int,
) -> None:
    if value is None:
        return
    if not value.strip():
        raise ValueError(f"{field_name} must not be blank")
    if len(value) > maximum_length:
        raise ValueError(f"{field_name} must not exceed {maximum_length} characters")


def _list_item(record: ProcessingRunListRecord) -> ProcessingRunListItem:
    return ProcessingRunListItem(
        processing_run_id=record.processing_run_id,
        event_id=record.event_id,
        source=record.source,
        external_reference=record.external_reference,
        started_at=record.started_at,
        completed_at=record.completed_at,
        final_status=record.final_status,
        rules_engine_version=record.rules_engine_version,
    )
