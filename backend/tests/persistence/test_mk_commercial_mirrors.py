from dataclasses import fields, replace
from datetime import UTC, datetime
from decimal import Decimal

from supervisor_ai.application.mk_operational import (
    MK_ATTENDANCE_PLAN_CHANGE_LINK_POLICY,
    MkContractMirror,
    MkContractPlanChangeMirror,
    MkPlanMirror,
    MkUpsertOutcome,
    mk_user_external_identity,
)
from supervisor_ai.infrastructure.external.mk.time import mk_local_datetime_to_utc
from supervisor_ai.infrastructure.persistence.mk_operational import (
    SqlAlchemyMkContractMirrorRepository,
    SqlAlchemyMkContractPlanChangeMirrorRepository,
    SqlAlchemyMkPlanMirrorRepository,
)

SEEN = datetime(2026, 8, 27, 12, tzinfo=UTC)
LATER = datetime(2026, 8, 27, 13, tzinfo=UTC)


def plan() -> MkPlanMirror:
    return MkPlanMirror(
        "8", "Plano", Decimal("99.90"), 500, 250, "500/250", SEEN, SEEN, SEEN, SEEN
    )


def contract() -> MkContractMirror:
    return MkContractMirror(
        "91", "52", "8", "N", "N", None, None, SEEN, SEEN, SEEN, SEEN
    )


def change(external_id: str = "100", **updates: object) -> MkContractPlanChangeMirror:
    values = {
        "external_id": external_id,
        "contract_external_id": "91",
        "operation_code": 4,
        "old_plan_external_id": "7",
        "new_plan_external_id": "8",
        "changed_at": mk_local_datetime_to_utc(datetime(2025, 1, 1, 9)),
        "changed_by_login": "operator",
        "changed_by_operator_external_id": "31",
        "value_delta": Decimal("20.00"),
        "extra_context": None,
        "source_first_seen_at": SEEN,
        "source_last_seen_at": SEEN,
        "local_created_at": SEEN,
        "local_updated_at": SEEN,
    }
    values.update(updates)
    return MkContractPlanChangeMirror(**values)  # type: ignore[arg-type]


def test_mutable_upserts_and_seen_only_change(session_factory) -> None:
    with session_factory() as session:
        plans = SqlAlchemyMkPlanMirrorRepository(session)
        contracts = SqlAlchemyMkContractMirrorRepository(session)
        changes = SqlAlchemyMkContractPlanChangeMirrorRepository(session)
        assert plans.upsert(plan()) is MkUpsertOutcome.INSERTED
        assert contracts.upsert(contract()) is MkUpsertOutcome.INSERTED
        original = change()
        assert changes.upsert(original) is MkUpsertOutcome.INSERTED
        assert (
            changes.upsert(replace(original, source_last_seen_at=LATER))
            is MkUpsertOutcome.UNCHANGED
        )
        corrected = replace(
            original, value_delta=Decimal("25.00"), local_updated_at=LATER
        )
        assert changes.upsert(corrected) is MkUpsertOutcome.UPDATED
        assert changes.get_by_external_id("100").value_delta == Decimal("25.00")  # type: ignore[union-attr]


def test_out_of_order_multiple_changes_and_operator_resolution(session_factory) -> None:
    with session_factory() as session:
        repository = SqlAlchemyMkContractPlanChangeMirrorRepository(session)
        repository.upsert(change("100"))
        repository.upsert(
            change(
                "101",
                operation_code=5,
                old_plan_external_id="8",
                new_plan_external_id="9",
                changed_by_operator_external_id=None,
            )
        )
        assert [
            (item.old_plan_external_id, item.new_plan_external_id)
            for item in repository.list_by_contract("91")
        ] == [("7", "8"), ("8", "9")]
        assert mk_user_external_identity(31) == "31"
        assert (
            repository.get_by_external_id("101").changed_by_operator_external_id is None
        )  # type: ignore[union-attr]


def test_null_plans_unknown_operation_timestamp_and_attendance_policy() -> None:
    item = change(
        "102", operation_code=99, old_plan_external_id=None, new_plan_external_id=None
    )
    assert item.changed_at == datetime(2025, 1, 1, 12, tzinfo=UTC)
    assert item.old_plan_external_id is item.new_plan_external_id is None
    assert MK_ATTENDANCE_PLAN_CHANGE_LINK_POLICY == "temporal_link_rejected"
    assert not (
        {"attendance_id", "ticket_id", "protocol"}
        & {field.name for field in fields(item)}
    )
