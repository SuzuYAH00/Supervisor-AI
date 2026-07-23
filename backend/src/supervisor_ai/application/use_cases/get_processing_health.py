from dataclasses import dataclass
from datetime import date

from supervisor_ai.application.persistence import ProcessingHealthCount
from supervisor_ai.application.ports import UnitOfWorkFactory

MAX_PROCESSING_HEALTH_SOURCE_LENGTH = 100
MAX_RULES_ENGINE_VERSION_LENGTH = 100


@dataclass(frozen=True, slots=True)
class GetProcessingHealthQuery:
    start_date: date | None = None
    end_date: date | None = None
    source: str | None = None
    rules_engine_version: str | None = None

    def __post_init__(self) -> None:
        _validate_optional_text(
            self.source,
            "source",
            MAX_PROCESSING_HEALTH_SOURCE_LENGTH,
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


@dataclass(frozen=True, slots=True)
class ProcessingRunHealth:
    total: int
    by_final_status: tuple[ProcessingHealthCount, ...]
    by_rules_engine_version: tuple[ProcessingHealthCount, ...]


@dataclass(frozen=True, slots=True)
class CommercialEventProcessingHealth:
    events_with_processing_runs: int
    events_without_processing_runs: int
    events_with_multiple_processing_runs: int
    events_with_ledger_entries: int
    events_without_ledger_entries: int


@dataclass(frozen=True, slots=True)
class GetProcessingHealthResult:
    filters: GetProcessingHealthQuery
    processing_runs: ProcessingRunHealth
    commercial_events: CommercialEventProcessingHealth


class GetProcessingHealthUseCase:
    """Consulta métricas factuais persistidas sem diagnosticar saúde."""

    def __init__(self, unit_of_work_factory: UnitOfWorkFactory) -> None:
        self._unit_of_work_factory = unit_of_work_factory

    def execute(self, query: GetProcessingHealthQuery) -> GetProcessingHealthResult:
        with self._unit_of_work_factory() as unit_of_work:
            record = unit_of_work.processing_health.get_processing_health(
                start_date=query.start_date,
                end_date=query.end_date,
                source=query.source,
                rules_engine_version=query.rules_engine_version,
            )
        return GetProcessingHealthResult(
            filters=query,
            processing_runs=ProcessingRunHealth(
                total=record.processing_run_total,
                by_final_status=tuple(
                    sorted(record.by_final_status, key=lambda item: item.value)
                ),
                by_rules_engine_version=tuple(
                    sorted(
                        record.by_rules_engine_version,
                        key=lambda item: item.value,
                    )
                ),
            ),
            commercial_events=CommercialEventProcessingHealth(
                events_with_processing_runs=record.events_with_processing_runs,
                events_without_processing_runs=record.events_without_processing_runs,
                events_with_multiple_processing_runs=(
                    record.events_with_multiple_processing_runs
                ),
                events_with_ledger_entries=record.events_with_ledger_entries,
                events_without_ledger_entries=record.events_without_ledger_entries,
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
