from dataclasses import replace
from datetime import UTC, datetime

from sqlalchemy import func, select

from supervisor_ai.application.mk_operational import (
    MK_SOURCE,
    MkAttendanceMirror,
    MkBotConversationMirror,
    MkSyncRun,
    MkSyncState,
    MkSyncStatus,
    MkUpsertOutcome,
)
from supervisor_ai.infrastructure.external.mk.time import mk_local_datetime_to_utc
from supervisor_ai.infrastructure.persistence.mk_operational import (
    SqlAlchemyMkAttendanceMirrorRepository,
    SqlAlchemyMkBotConversationMirrorRepository,
    SqlAlchemyMkSyncRepository,
)
from supervisor_ai.infrastructure.persistence.models import (
    MkAttendanceMirrorRecord,
    MkBotConversationMirrorRecord,
)
from supervisor_ai.infrastructure.persistence.unit_of_work import SqlAlchemyUnitOfWork

SEEN = datetime(2026, 8, 26, 12, tzinfo=UTC)
LATER = datetime(2026, 8, 26, 13, tzinfo=UTC)


def attendance(external_id: str = "9001", **changes: object) -> MkAttendanceMirror:
    values: dict[str, object] = {
        "external_id": external_id,
        "protocol": "2699.10180",
        "customer_external_id": "customer-fixture",
        "opened_at": datetime(2026, 8, 24, 13, tzinfo=UTC),
        "closed_at": None,
        "opening_operator_external_id": "7001",
        "closing_operator_external_id": None,
        "process_external_id": "process-1",
        "subprocess_external_id": "subprocess-1",
        "opening_classification_external_id": "class-1",
        "closing_classification_external_id": None,
        "origin_external_id": "origin-1",
        "status": "open",
        "is_finalized": False,
        "mk_dialog_session_external_id": None,
        "source_first_seen_at": SEEN,
        "source_last_seen_at": SEEN,
        "local_created_at": SEEN,
        "local_updated_at": SEEN,
    }
    values.update(changes)
    return MkAttendanceMirror(**values)  # type: ignore[arg-type]


def conversation(**changes: object) -> MkBotConversationMirror:
    values: dict[str, object] = {
        "external_id": "dialog-1",
        "protocol": "2699.20180",
        "person_external_id": "person-fixture",
        "integration_external_reference": "integration-fixture",
        "conversation_type": "Whatsapp",
        "sector_external_id": "sector-1",
        "created_at": datetime(2026, 8, 24, 13, tzinfo=UTC),
        "human_service_started_at": datetime(2026, 8, 24, 13, 2, tzinfo=UTC),
        "queue_entered_at": datetime(2026, 8, 24, 13, 1, tzinfo=UTC),
        "closed_at": None,
        "score": None,
        "final_operator_external_id": None,
        "source_first_seen_at": SEEN,
        "source_last_seen_at": SEEN,
        "local_created_at": SEEN,
        "local_updated_at": SEEN,
    }
    values.update(changes)
    return MkBotConversationMirror(**values)  # type: ignore[arg-type]


def test_attendance_upsert_is_mutable_idempotent_and_preserves_protocol(
    session_factory,
) -> None:
    with session_factory() as session:
        repository = SqlAlchemyMkAttendanceMirrorRepository(session)
        original = attendance()
        assert repository.upsert(original) is MkUpsertOutcome.INSERTED
        assert (
            repository.upsert(replace(original, source_last_seen_at=LATER))
            is MkUpsertOutcome.UNCHANGED
        )

        closed = replace(
            original,
            closed_at=datetime(2026, 8, 24, 14, tzinfo=UTC),
            closing_operator_external_id="7002",
            status="closed",
            is_finalized=True,
            source_last_seen_at=LATER,
            local_updated_at=LATER,
        )
        assert repository.upsert(closed) is MkUpsertOutcome.UPDATED
        assert repository.upsert(attendance("9002")) is MkUpsertOutcome.INSERTED
        session.commit()

    with session_factory() as session:
        repository = SqlAlchemyMkAttendanceMirrorRepository(session)
        persisted = repository.get_by_external_id("9001")
        assert persisted is not None
        assert persisted.protocol == "2699.10180"
        assert persisted.closed_at == datetime(2026, 8, 24, 14, tzinfo=UTC)
        assert persisted.closing_operator_external_id == "7002"
        assert (
            session.scalar(select(func.count()).select_from(MkAttendanceMirrorRecord))
            == 2
        )


def test_mkbot_upsert_preserves_null_then_accepts_evaluation_and_close(
    session_factory,
) -> None:
    with session_factory() as session:
        repository = SqlAlchemyMkBotConversationMirrorRepository(session)
        original = conversation()
        assert repository.upsert(original) is MkUpsertOutcome.INSERTED
        assert repository.get_by_external_id("dialog-1").score is None  # type: ignore[union-attr]
        assert repository.upsert(original) is MkUpsertOutcome.UNCHANGED
        finished = replace(
            original,
            score=5,
            final_operator_external_id="7003",
            closed_at=datetime(2026, 8, 24, 14, tzinfo=UTC),
            source_last_seen_at=LATER,
            local_updated_at=LATER,
        )
        assert repository.upsert(finished) is MkUpsertOutcome.UPDATED
        session.commit()

    with session_factory() as session:
        persisted = SqlAlchemyMkBotConversationMirrorRepository(
            session
        ).get_by_external_id("dialog-1")
        assert persisted is not None
        assert persisted.score == 5
        assert persisted.final_operator_external_id == "7003"
        assert persisted.queue_entered_at is not None
        assert persisted.human_service_started_at is not None
        assert (
            session.scalar(
                select(func.count()).select_from(MkBotConversationMirrorRecord)
            )
            == 1
        )


def test_dialog_relation_accepts_pending_and_one_to_many(session_factory) -> None:
    with session_factory() as session:
        attendances = SqlAlchemyMkAttendanceMirrorRepository(session)
        conversations = SqlAlchemyMkBotConversationMirrorRepository(session)
        attendances.upsert(
            attendance("9001", mk_dialog_session_external_id="dialog-pending")
        )
        attendances.upsert(attendance("9002"))
        session.flush()
        assert (
            len(attendances.list_by_dialog_session_external_id("dialog-pending")) == 1
        )

        conversations.upsert(conversation(external_id="dialog-pending"))
        attendances.upsert(
            attendance("9002", mk_dialog_session_external_id="dialog-pending")
        )
        related = attendances.list_by_dialog_session_external_id("dialog-pending")
        assert [item.external_id for item in related] == ["9001", "9002"]
        assert all(item.protocol != "2699.20180" for item in related)


def test_sync_state_run_and_error_sanitization(session_factory) -> None:
    with session_factory() as session:
        repository = SqlAlchemyMkSyncRepository(session)
        assert repository.get_state(source=MK_SOURCE, entity_type="attendance") is None
        state = MkSyncState(
            source=MK_SOURCE,
            entity_type="attendance",
            last_pk=None,
            last_success_at=None,
            last_attempt_at=SEEN,
            status=MkSyncStatus.RUNNING,
            last_error=None,
            created_at=SEEN,
            updated_at=SEEN,
        )
        repository.save_state(state)
        repository.save_state(
            replace(
                state,
                last_pk=9002,
                last_success_at=LATER,
                status=MkSyncStatus.SUCCEEDED,
                last_error="password=secret token=secret",
                updated_at=LATER,
            )
        )
        run = MkSyncRun(
            id="run-fixture",
            source=MK_SOURCE,
            entity_type="attendance",
            initial_cursor=None,
            final_cursor=None,
            inserted=0,
            updated=0,
            unchanged=0,
            rejected=0,
            status=MkSyncStatus.RUNNING,
            started_at=SEEN,
            finished_at=None,
            error=None,
            created_at=SEEN,
        )
        repository.add_run(run)
        repository.update_run(
            replace(
                run,
                final_cursor=9002,
                inserted=2,
                status=MkSyncStatus.SUCCEEDED,
                finished_at=LATER,
            )
        )
        session.commit()

    with session_factory() as session:
        repository = SqlAlchemyMkSyncRepository(session)
        persisted_state = repository.get_state(
            source=MK_SOURCE, entity_type="attendance"
        )
        assert persisted_state is not None
        assert persisted_state.last_pk == 9002
        assert persisted_state.last_success_at == LATER
        assert "secret" not in (persisted_state.last_error or "")
        assert repository.get_run("run-fixture").inserted == 2  # type: ignore[union-attr]


def test_batch_and_cursor_can_rollback_atomically(session_factory) -> None:
    with session_factory() as session:
        SqlAlchemyMkAttendanceMirrorRepository(session).upsert(attendance())
        SqlAlchemyMkSyncRepository(session).save_state(
            MkSyncState(
                source=MK_SOURCE,
                entity_type="attendance",
                last_pk=9001,
                last_success_at=LATER,
                last_attempt_at=LATER,
                status=MkSyncStatus.SUCCEEDED,
                last_error=None,
                created_at=SEEN,
                updated_at=LATER,
            )
        )
        session.rollback()

    with session_factory() as session:
        assert (
            SqlAlchemyMkAttendanceMirrorRepository(session).get_by_external_id("9001")
            is None
        )
        assert (
            SqlAlchemyMkSyncRepository(session).get_state(
                source=MK_SOURCE, entity_type="attendance"
            )
            is None
        )


def test_mk_fortaleza_naive_timestamp_is_normalized_to_utc() -> None:
    assert mk_local_datetime_to_utc(datetime(2026, 8, 24, 10, 30)) == datetime(
        2026, 8, 24, 13, 30, tzinfo=UTC
    )


def test_unit_of_work_exposes_local_mirrors_in_one_transaction(
    session_factory,
) -> None:
    with SqlAlchemyUnitOfWork(session_factory) as unit_of_work:
        unit_of_work.mk_attendances.upsert(attendance())
        unit_of_work.mkbot_conversations.upsert(conversation())
        unit_of_work.mk_sync.save_state(
            MkSyncState(
                source=MK_SOURCE,
                entity_type="attendance",
                last_pk=9001,
                last_success_at=LATER,
                last_attempt_at=LATER,
                status=MkSyncStatus.SUCCEEDED,
                last_error=None,
                created_at=SEEN,
                updated_at=LATER,
            )
        )
        unit_of_work.commit()

    with SqlAlchemyUnitOfWork(session_factory) as unit_of_work:
        assert unit_of_work.mk_attendances.get_by_external_id("9001") is not None
        assert (
            unit_of_work.mkbot_conversations.get_by_external_id("dialog-1") is not None
        )
        assert (
            unit_of_work.mk_sync.get_state(source=MK_SOURCE, entity_type="attendance")
            is not None
        )


def test_open_lists_include_only_mutable_records(session_factory) -> None:
    with session_factory() as session:
        attendances = SqlAlchemyMkAttendanceMirrorRepository(session)
        attendances.upsert(attendance("open"))
        attendances.upsert(
            attendance("closed", closed_at=datetime(2026, 8, 24, 14, tzinfo=UTC))
        )
        conversations = SqlAlchemyMkBotConversationMirrorRepository(session)
        conversations.upsert(conversation(external_id="open-dialog"))
        conversations.upsert(
            conversation(
                external_id="closed-dialog",
                closed_at=datetime(2026, 8, 24, 14, tzinfo=UTC),
            )
        )
        assert [item.external_id for item in attendances.list_open()] == ["open"]
        assert [item.external_id for item in conversations.list_open()] == [
            "open-dialog"
        ]
