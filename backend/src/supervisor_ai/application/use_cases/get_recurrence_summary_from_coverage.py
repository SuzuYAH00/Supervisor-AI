from dataclasses import dataclass
from datetime import date

from supervisor_ai.application.errors import IngestionCoverageUnknown
from supervisor_ai.application.ports import UnitOfWorkFactory
from supervisor_ai.application.recurrence import RecurrenceCohortQuery
from supervisor_ai.application.use_cases.get_recurrence_summary import (
    GetRecurrenceSummaryResult,
    GetRecurrenceSummaryUseCase,
)
from supervisor_ai.application.use_cases.import_attendances import (
    RECURRENCE_ATTENDANCES_DATASET,
)


@dataclass(frozen=True, slots=True)
class GetRecurrenceSummaryFromCoverageQuery:
    reference_month: date
    source: str

    def __post_init__(self) -> None:
        if self.reference_month.day != 1:
            raise ValueError("reference_month must be the first day of a month")
        if not self.source.strip():
            raise ValueError("source must not be blank")


class GetRecurrenceSummaryFromCoverageUseCase:
    """Fecha a coorte somente com evidência persistida da fonte."""

    def __init__(
        self,
        unit_of_work_factory: UnitOfWorkFactory,
        summary: GetRecurrenceSummaryUseCase,
    ) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._summary = summary

    def execute(
        self, query: GetRecurrenceSummaryFromCoverageQuery
    ) -> GetRecurrenceSummaryResult:
        with self._unit_of_work_factory() as unit_of_work:
            coverage = unit_of_work.ingestion_coverages.get_latest(
                dataset=RECURRENCE_ATTENDANCES_DATASET,
                source=query.source,
            )
        if coverage is None:
            raise IngestionCoverageUnknown(
                "recurrence attendance coverage is unknown for the source"
            )
        return self._summary.execute(
            RecurrenceCohortQuery(
                reference_month=query.reference_month,
                observed_through=coverage.covered_through,
                source=query.source,
            )
        )
