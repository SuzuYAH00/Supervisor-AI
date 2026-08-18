from datetime import UTC, date, datetime

from sqlalchemy.orm import Session, sessionmaker

from supervisor_ai.application import IngestionCoverageEvidence
from supervisor_ai.infrastructure.persistence.unit_of_work import (
    SqlAlchemyUnitOfWork,
)


def test_coverage_persists_across_units_of_work_and_keeps_latest(
    session_factory: sessionmaker[Session],
) -> None:
    older = IngestionCoverageEvidence(
        dataset="recurrence_attendances",
        source="local-export",
        import_reference="export-a",
        covered_through=date(2026, 8, 10),
        recorded_at=datetime(2026, 8, 11, tzinfo=UTC),
    )
    newer = IngestionCoverageEvidence(
        dataset="recurrence_attendances",
        source="local-export",
        import_reference="export-b",
        covered_through=date(2026, 8, 20),
        recorded_at=datetime(2026, 8, 21, tzinfo=UTC),
    )
    with SqlAlchemyUnitOfWork(session_factory) as unit_of_work:
        unit_of_work.ingestion_coverages.add(older)
        unit_of_work.ingestion_coverages.add(newer)
        unit_of_work.commit()

    with SqlAlchemyUnitOfWork(session_factory) as unit_of_work:
        assert unit_of_work.ingestion_coverages.get_by_import_reference(
            dataset=older.dataset,
            source=older.source,
            import_reference=older.import_reference,
        ) == older
        assert unit_of_work.ingestion_coverages.get_latest(
            dataset=older.dataset,
            source=older.source,
        ) == newer
