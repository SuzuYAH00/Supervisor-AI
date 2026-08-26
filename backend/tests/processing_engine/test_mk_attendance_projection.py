from dataclasses import replace
from datetime import UTC, date, datetime

from supervisor_ai.application import (
    CollaboratorExternalIdentity,
    OperationalCollaboratorProfile,
)
from supervisor_ai.application.mk_operational import (
    MK_ATTENDANCE_FACT_SOURCE,
    MkAttendanceMirror,
)
from supervisor_ai.infrastructure.persistence.unit_of_work import SqlAlchemyUnitOfWork
from supervisor_ai.processing_engine.mk_attendance_projection import (
    MkAttendanceCatalog,
    MkAttendanceProjectionStatus,
    MkResponsibleOperatorRole,
    ProjectMkAttendancesCommand,
    ProjectMkAttendancesUseCase,
)
from supervisor_ai.processing_engine.recurrence_regression import (
    RecurrenceRegressionDifference,
    compare_recurrence_paths,
)
from supervisor_ai.rules_engine import (
    ELIGIBLE_CLOSING_CLASSIFICATIONS,
    ELIGIBLE_OPENING_CLASSIFICATIONS,
    ELIGIBLE_PROCESS,
    CsatCompetitiveChannel,
    RecurrenceAttendance,
    find_recurrences,
)

NOW = datetime(2026, 8, 26, 12, tzinfo=UTC)
OPENING = next(item for item in ELIGIBLE_OPENING_CLASSIFICATIONS if item.code == "001")
CLOSING = next(item for item in ELIGIBLE_CLOSING_CLASSIFICATIONS if item.code == "001")
CATALOG = MkAttendanceCatalog(
    processes={"44": ELIGIBLE_PROCESS},
    opening_classifications={"81": OPENING},
    closing_classifications={"91": CLOSING},
    channels={"9": "phone"},
    responsible_operator_role=MkResponsibleOperatorRole.CLOSING,
)


def mirror(external_id: str, **changes: object) -> MkAttendanceMirror:
    values: dict[str, object] = {
        "external_id": external_id,
        "protocol": f"2607.{external_id}0",
        "customer_external_id": "148446",
        "opened_at": datetime(2026, 7, 13, 14, tzinfo=UTC),
        "closed_at": datetime(2026, 7, 13, 15, tzinfo=UTC),
        "opening_operator_external_id": "1491",
        "closing_operator_external_id": "1788",
        "process_external_id": "44",
        "subprocess_external_id": "71",
        "opening_classification_external_id": "81",
        "closing_classification_external_id": "91",
        "origin_external_id": "9",
        "status": "closed",
        "is_finalized": True,
        "mk_dialog_session_external_id": None,
        "source_first_seen_at": NOW,
        "source_last_seen_at": NOW,
        "local_created_at": NOW,
        "local_updated_at": NOW,
    }
    values.update(changes)
    return MkAttendanceMirror(**values)  # type: ignore[arg-type]


def seed(session_factory, *mirrors: MkAttendanceMirror, mapped=True) -> None:
    with SqlAlchemyUnitOfWork(session_factory) as unit_of_work:
        if mapped:
            unit_of_work.operational_collaborators.add(
                OperationalCollaboratorProfile(
                    "collaborator-1", CsatCompetitiveChannel.PHONE, NOW
                )
            )
            unit_of_work.collaborator_external_identities.add(
                CollaboratorExternalIdentity("collaborator-1", "mk", "1788", NOW)
            )
        for item in mirrors:
            unit_of_work.mk_attendances.upsert(item)
        unit_of_work.commit()


def project(session_factory, *, batch_size=500):
    return ProjectMkAttendancesUseCase(
        lambda: SqlAlchemyUnitOfWork(session_factory),
        lambda: NOW,
        CATALOG,
    ).execute(
        ProjectMkAttendancesCommand(date(2026, 7, 1), date(2026, 7, 31), batch_size)
    )


def test_projects_final_mirror_idempotently_with_provenance(session_factory) -> None:
    seed(session_factory, mirror("1505440"))

    first = project(session_factory)
    second = project(session_factory)

    assert first.count(MkAttendanceProjectionStatus.PROJECTED) == 1
    assert second.count(MkAttendanceProjectionStatus.UNCHANGED) == 1
    with SqlAlchemyUnitOfWork(session_factory) as unit_of_work:
        fact = unit_of_work.attendances.get_by_source_reference(
            source=MK_ATTENDANCE_FACT_SOURCE, external_reference="1505440"
        )
        assert fact is not None
        assert fact.id == "mk-attendance:1505440"
        assert fact.customer_code == "148446"
        assert fact.operator_id == "collaborator-1"
        assert fact.occurred_at == datetime(2026, 7, 13, 14, tzinfo=UTC)


def test_open_and_unresolved_records_are_structured_not_silently_dropped(
    session_factory,
) -> None:
    seed(
        session_factory,
        mirror("1", closed_at=None, is_finalized=False),
        mirror("2", closing_operator_external_id="9999"),
    )

    result = project(session_factory)

    assert [item.status for item in result.items] == [
        MkAttendanceProjectionStatus.NOT_READY_FOR_PROJECTION,
        MkAttendanceProjectionStatus.UNRESOLVED_OPERATOR,
    ]


def test_unknown_catalog_is_not_fabricated(session_factory) -> None:
    seed(session_factory, mirror("1", process_external_id="unknown"))
    result = project(session_factory)
    assert result.items[0].status is MkAttendanceProjectionStatus.UNRESOLVED_CATALOG
    assert result.items[0].missing_fields == ("process_external_id",)


def test_five_same_day_attendances_remain_distinct_and_order_by_timestamp(
    session_factory,
) -> None:
    times = (
        ("1505906", 14),
        ("1505440", 21),
        ("1505756", 18),
        ("1505801", 19),
        ("1505871", 20),
    )
    seed(
        session_factory,
        *(
            mirror(external_id, opened_at=datetime(2026, 7, 13, hour, tzinfo=UTC))
            for external_id, hour in times
        ),
    )
    result = project(session_factory, batch_size=2)
    assert result.count(MkAttendanceProjectionStatus.PROJECTED) == 5

    with SqlAlchemyUnitOfWork(session_factory) as unit_of_work:
        facts = unit_of_work.attendances.search(
            operator_id=None,
            customer_code="148446",
            source=MK_ATTENDANCE_FACT_SOURCE,
            channel=None,
            start_date=date(2026, 7, 13),
            end_date=date(2026, 7, 13),
        )
    assert len(facts) == 5
    assert [item.external_reference for item in facts] == [
        "1505906",
        "1505756",
        "1505801",
        "1505871",
        "1505440",
    ]
    recurrence_input = tuple(
        RecurrenceAttendance(
            item.id,
            item.customer_code,
            item.operator_id,
            item.channel,
            item.occurred_at,
            item.process,
            item.opening_classification,
            item.closing_classification,
        )
        for item in facts
    )
    assert (
        len(
            find_recurrences(
                recurrence_input,
                cohort_start=date(2026, 7, 1),
                cohort_end=date(2026, 7, 31),
            )
        )
        == 4
    )


def test_protocol_text_is_preserved_and_distinct(session_factory) -> None:
    seed(
        session_factory,
        mirror("1", protocol="2607.10180"),
        mirror("2", protocol="2607.1018"),
    )
    result = project(session_factory)
    assert [item.protocol for item in result.items] == ["2607.10180", "2607.1018"]
    assert result.items[0].protocol != result.items[1].protocol


def test_projection_period_uses_fortaleza_month_boundaries(session_factory) -> None:
    seed(
        session_factory,
        mirror("1", opened_at=datetime(2026, 7, 1, 3, tzinfo=UTC)),
        mirror("2", opened_at=datetime(2026, 8, 1, 2, 59, 59, tzinfo=UTC)),
        mirror("3", opened_at=datetime(2026, 8, 1, 3, tzinfo=UTC)),
    )

    result = project(session_factory)

    assert [item.external_id for item in result.items] == ["1", "2"]


def test_regression_comparator_reuses_rule_and_explains_legacy_precision(
    session_factory,
) -> None:
    seed(session_factory, mirror("1"))
    project(session_factory)
    with SqlAlchemyUnitOfWork(session_factory) as unit_of_work:
        mk_fact = unit_of_work.attendances.get_by_source_reference(
            source=MK_ATTENDANCE_FACT_SOURCE, external_reference="1"
        )
    assert mk_fact is not None
    legacy = replace(
        mk_fact,
        id="legacy-1",
        source="mk",
        external_reference="legacy-protocol",
        occurred_at=datetime(2026, 7, 13, tzinfo=UTC),
    )
    result = compare_recurrence_paths(
        (legacy,),
        (mk_fact,),
        cohort_start=date(2026, 7, 1),
        cohort_end=date(2026, 7, 31),
        legacy_protocols={legacy.id: "2607.1018"},
        mk_protocols={mk_fact.id: "2607.10180"},
    )
    assert result.legacy_recurrence_count == result.mk_recurrence_count
    assert {item.category for item in result.issues} == {
        RecurrenceRegressionDifference.LEGACY_DATE_ONLY,
        RecurrenceRegressionDifference.LEGACY_PROTOCOL_CORRUPTION,
    }
