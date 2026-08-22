from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy.orm import Session, sessionmaker

from supervisor_ai.application.errors import DelayReviewConflict
from supervisor_ai.application.persistence import (
    CollaboratorExternalIdentity,
    DailyPlannedWorkScheduleFact,
    DelayOccurrence,
    EmployeeOccurrenceReport,
    OperationalCollaboratorProfile,
)
from supervisor_ai.application.use_cases.npx_delays import (
    GetMonthlyDelayCountQuery,
    GetMonthlyDelayCountUseCase,
    ImportNpxFactsCommand,
    ImportNpxFactsUseCase,
    NpxCoverageDeclaration,
    PauseInput,
    RecordDelayReviewCommand,
    RecordDelayReviewUseCase,
    WorkSessionInput,
)
from supervisor_ai.application.use_cases.operational_delays import (
    GetOperationalDelaysQuery,
    GetOperationalDelaysUseCase,
)
from supervisor_ai.infrastructure.persistence.unit_of_work import SqlAlchemyUnitOfWork
from supervisor_ai.rules_engine import CsatCompetitiveChannel
from supervisor_ai.rules_engine.delays import DelayDecision

NOW = datetime(2026, 8, 18, 12, tzinfo=UTC)


def _factory(session_factory: sessionmaker[Session]):
    return lambda: SqlAlchemyUnitOfWork(session_factory)


def _setup(session_factory: sessionmaker[Session]) -> None:
    with SqlAlchemyUnitOfWork(session_factory) as uow:
        uow.operational_collaborators.add(
            OperationalCollaboratorProfile(
                "operator-2", CsatCompetitiveChannel.PHONE, NOW
            )
        )
        uow.operational_collaborators.add(
            OperationalCollaboratorProfile(
                "operator-1", CsatCompetitiveChannel.CHAT, NOW
            )
        )
        uow.collaborator_external_identities.add(
            CollaboratorExternalIdentity("operator-1", "npx", "Agent Test", NOW)
        )
        uow.commit()


def _pause(identity: str = "Agent Test") -> PauseInput:
    start = datetime(2026, 8, 3, 10, tzinfo=UTC)
    return PauseInput(
        "pause-1",
        "npx-pause-1",
        identity,
        "001",
        "Support",
        start,
        start + timedelta(minutes=21),
        1260,
        "extract-1",
        "Sheet1",
        3,
        "Intervalo 20min",
        "NÃO",
    )


def _session() -> WorkSessionInput:
    start = datetime(2026, 8, 3, 8, 40, tzinfo=UTC)
    return WorkSessionInput(
        "session-1",
        "npx-session-1",
        "Agent Test",
        "001",
        "Support",
        start,
        start + timedelta(hours=6),
        21600,
        "extract-1",
        "Sheet1",
        3,
    )


def test_import_is_idempotent_derives_delay_and_records_coverage(
    session_factory: sessionmaker[Session],
) -> None:
    _setup(session_factory)
    service = ImportNpxFactsUseCase(_factory(session_factory), lambda: NOW)
    command = ImportNpxFactsCommand(
        pauses=(_pause(),),
        pause_coverage=NpxCoverageDeclaration(date(2026, 8, 31), "extract-1"),
    )
    first = service.execute(command)
    second = service.execute(command)

    assert first.imported_pauses == 1
    assert first.delay_occurrences_created == 1
    assert second.idempotent_rows == 1
    assert second.delay_occurrences_created == 0
    assert (
        GetMonthlyDelayCountUseCase(_factory(session_factory))
        .execute(GetMonthlyDelayCountQuery("operator-1", date(2026, 8, 1)))
        .delay_count
        == 1
    )
    with SqlAlchemyUnitOfWork(session_factory) as uow:
        assert uow.ingestion_coverages.get_latest(
            dataset="npx_pauses", source="npx"
        ).covered_through == date(2026, 8, 31)


def test_unknown_alias_is_rejected_without_fuzzy_matching(
    session_factory: sessionmaker[Session],
) -> None:
    _setup(session_factory)
    result = ImportNpxFactsUseCase(_factory(session_factory), lambda: NOW).execute(
        ImportNpxFactsCommand(pauses=(_pause("Agent  Test"),))
    )
    assert result.rejected_rows == 1
    assert result.issues[0].code == "unknown_collaborator_alias"


def test_work_session_is_persisted_but_does_not_invent_entry_delay(
    session_factory: sessionmaker[Session],
) -> None:
    _setup(session_factory)
    service = ImportNpxFactsUseCase(_factory(session_factory), lambda: NOW)
    command = ImportNpxFactsCommand(work_sessions=(_session(),))
    assert service.execute(command).imported_work_sessions == 1
    assert service.execute(command).idempotent_rows == 1
    with SqlAlchemyUnitOfWork(session_factory) as uow:
        assert (
            len(
                uow.work_sessions.search_date(
                    collaborator_id="operator-1", work_date=date(2026, 8, 3)
                )
            )
            == 1
        )
        assert not uow.delay_occurrences.search_month(
            collaborator_id="operator-1", competence_month=date(2026, 8, 1)
        )


def test_corrected_review_removes_delay_from_count(
    session_factory: sessionmaker[Session],
) -> None:
    _setup(session_factory)
    factory = _factory(session_factory)
    ImportNpxFactsUseCase(factory, lambda: NOW).execute(
        ImportNpxFactsCommand(pauses=(_pause(),))
    )
    with SqlAlchemyUnitOfWork(session_factory) as uow:
        occurrence = uow.delay_occurrences.search_month(
            collaborator_id="operator-1", competence_month=date(2026, 8, 1)
        )[0]
    RecordDelayReviewUseCase(factory, lambda: NOW).execute(
        RecordDelayReviewCommand(
            "review-1",
            occurrence.id,
            DelayDecision.CORRECTED,
            NOW,
            "supervisor-1",
        )
    )
    assert (
        GetMonthlyDelayCountUseCase(factory)
        .execute(GetMonthlyDelayCountQuery("operator-1", date(2026, 8, 1)))
        .delay_count
        == 0
    )


def test_valid_review_keeps_delay_countable(
    session_factory: sessionmaker[Session],
) -> None:
    _setup(session_factory)
    factory = _factory(session_factory)
    ImportNpxFactsUseCase(factory, lambda: NOW).execute(
        ImportNpxFactsCommand(pauses=(_pause(),))
    )
    with SqlAlchemyUnitOfWork(session_factory) as uow:
        occurrence = uow.delay_occurrences.search_month(
            collaborator_id="operator-1", competence_month=date(2026, 8, 1)
        )[0]
    RecordDelayReviewUseCase(factory, lambda: NOW).execute(
        RecordDelayReviewCommand(
            "review-1", occurrence.id, DelayDecision.VALID, NOW, "supervisor-1"
        )
    )
    assert (
        GetMonthlyDelayCountUseCase(factory)
        .execute(GetMonthlyDelayCountQuery("operator-1", date(2026, 8, 1)))
        .delay_count
        == 1
    )


def test_operational_projection_filters_and_preserves_possible_evidence(
    session_factory: sessionmaker[Session],
) -> None:
    _setup(session_factory)
    factory = _factory(session_factory)
    ImportNpxFactsUseCase(factory, lambda: NOW).execute(
        ImportNpxFactsCommand(work_sessions=(_session(),), pauses=(_pause(),))
    )
    with SqlAlchemyUnitOfWork(session_factory) as uow:
        uow.daily_planned_work_schedules.add(
            DailyPlannedWorkScheduleFact(
                "schedule-entry",
                "operator-1",
                date(2026, 8, 3),
                datetime.min.time().replace(hour=5),
                datetime.min.time().replace(hour=11),
                "standard",
                "attendance_sheet",
                "schedule-ref",
                "AUGUST",
                "D3",
                created_at=NOW,
            )
        )
        uow.delay_occurrences.add(
            DelayOccurrence(
                "delay-entry",
                "operator-1",
                date(2026, 8, 3),
                "entry",
                "work_session",
                "session-1",
                5 * 3600 + 40 * 60,
                5 * 3600 + 59,
                NOW,
            )
        )
        uow.employee_occurrence_reports.add(
            EmployeeOccurrenceReport(
                "report-1",
                "forms-1",
                "google_forms_employee_occurrences",
                "operator-1",
                "Agent Test",
                NOW,
                date(2026, 8, 3),
                "Original employee statement",
                "Responses",
                2,
                NOW,
            )
        )
        uow.employee_occurrence_reports.add(
            EmployeeOccurrenceReport(
                "report-other-collaborator",
                "forms-3",
                "google_forms_employee_occurrences",
                "operator-2",
                "Other Agent",
                NOW,
                date(2026, 8, 3),
                "Statement from another collaborator",
                "Responses",
                4,
                NOW,
            )
        )
        uow.employee_occurrence_reports.add(
            EmployeeOccurrenceReport(
                "report-other-date",
                "forms-2",
                "google_forms_employee_occurrences",
                "operator-1",
                "Agent Test",
                NOW,
                date(2026, 8, 4),
                "Statement from another date",
                "Responses",
                3,
                NOW,
            )
        )
        uow.employee_occurrence_reports.add(
            EmployeeOccurrenceReport(
                "report-2",
                "forms-4",
                "google_forms_employee_occurrences",
                "operator-1",
                "Agent Test",
                NOW + timedelta(minutes=1),
                date(2026, 8, 3),
                "Second statement from the same date",
                "Responses",
                5,
                NOW,
            )
        )
        uow.commit()

    service = GetOperationalDelaysUseCase(factory)
    result = service.execute(
        GetOperationalDelaysQuery(
            date(2026, 8, 1),
            collaborator_id="operator-1",
            delay_type="pause_duration",
            review_status="pending_review",
        )
    )
    assert result.detected_count == 1
    assert result.pending_count == 1
    assert result.items[0].counts_for_rv is True
    assert [item.id for item in result.items[0].possible_reports] == [
        "report-1",
        "report-2",
    ]

    entry = service.execute(
        GetOperationalDelaysQuery(date(2026, 8, 1), delay_type="entry")
    )
    assert entry.items[0].source_fact.source_fact_type == "work_session"
    assert entry.items[0].schedule.planned_start.hour == 5

    occurrence_id = result.items[0].occurrence.id
    invalid_reports = (
        "missing-report",
        "report-other-date",
        "report-other-collaborator",
    )
    for report_id in invalid_reports:
        with pytest.raises(DelayReviewConflict):
            RecordDelayReviewUseCase(factory, lambda: NOW).execute(
                RecordDelayReviewCommand(
                    f"invalid-{report_id}",
                    occurrence_id,
                    DelayDecision.CORRECTED,
                    NOW,
                    "supervisor-1",
                    report_id,
                )
            )
    RecordDelayReviewUseCase(factory, lambda: NOW).execute(
        RecordDelayReviewCommand(
            "review-operational",
            occurrence_id,
            DelayDecision.CORRECTED,
            NOW,
            "supervisor-1",
            "report-1",
        )
    )
    corrected = service.execute(
        GetOperationalDelaysQuery(
            date(2026, 8, 1), review_status="corrected"
        )
    )
    assert corrected.corrected_count == 1
    assert corrected.items[0].counts_for_rv is False

    later = NOW + timedelta(minutes=1)
    RecordDelayReviewUseCase(factory, lambda: later).execute(
        RecordDelayReviewCommand(
            "review-later",
            occurrence_id,
            DelayDecision.VALID,
            later,
            "supervisor-1",
        )
    )
    latest = service.execute(
        GetOperationalDelaysQuery(date(2026, 8, 1), review_status="valid")
    )
    assert latest.items[0].current_review.id == "review-later"
    assert latest.items[0].counts_for_rv is True
    with SqlAlchemyUnitOfWork(session_factory) as uow:
        assert uow.delay_reviews.get_by_id("review-operational") is not None
        assert uow.delay_reviews.get_by_id("review-later") is not None
