from copy import deepcopy
from dataclasses import fields, replace
from datetime import UTC, datetime
from decimal import Decimal
from inspect import getsource

import pytest

import supervisor_ai.rules_engine.remuneration_ledger as ledger_module
from supervisor_ai.rules_engine import (
    Currency,
    ExistingLedgerEntryReference,
    LedgerEntry,
    LedgerEntryType,
    LedgerPostingInput,
    LedgerPostingReason,
    LedgerPostingResult,
    LedgerPostingStatus,
    RemunerationAmountReason,
    RemunerationAmountResult,
    RemunerationAmountStatus,
    RemunerationCalculationMethod,
    RemunerationLedgerPostingEvaluator,
    build_credit_entry_id,
)

POSTED_AT = datetime(2026, 7, 20, 12, tzinfo=UTC)


def amount_result(
    status: RemunerationAmountStatus = RemunerationAmountStatus.CALCULATED,
    *,
    event_id: str = "event:1",
    amount: object = Decimal("119.90"),
) -> RemunerationAmountResult:
    return RemunerationAmountResult(
        status=status,
        reasons=(RemunerationAmountReason.PAYMENT_VALIDATED,),
        event_id=event_id,
        remuneration_amount=amount,  # type: ignore[arg-type]
        calculation_method=RemunerationCalculationMethod.FULL_NEW_PLAN_AMOUNT,
        currency=Currency.BRL,
        payment_validation_reference="payment-validation:event:1",
        commercial_reference_ids=("commercial:1",),
        calculation_reference_ids=("calculation:1",),
    )


def posting_input(**changes: object) -> LedgerPostingInput:
    data = LedgerPostingInput(
        event_id="event:1",
        beneficiary_id="employee:42",
        remuneration_amount_result=amount_result(),
        posted_at=POSTED_AT,
        posting_reference="posting:payroll-2026-07",
        source_reference_ids=("source:invoice", "source:calculation"),
        remuneration_calculation_reference="remuneration-calculation:event:1",
        invoice_id="invoice:10",
    )
    return replace(data, **changes)


def evaluate(data: LedgerPostingInput) -> LedgerPostingResult:
    return RemunerationLedgerPostingEvaluator().evaluate(data)


def existing_entry(**changes: object) -> ExistingLedgerEntryReference:
    data = posting_input()
    entry = ExistingLedgerEntryReference(
        entry_id=build_credit_entry_id(data.event_id),
        event_id=data.event_id,
        beneficiary_id=data.beneficiary_id or "",
        entry_type=LedgerEntryType.CREDIT,
        amount=Decimal("119.90"),
        currency=Currency.BRL,
        posting_reference=data.posting_reference or "",
        source_reference_ids=data.source_reference_ids,
        remuneration_calculation_reference=(
            data.remuneration_calculation_reference or ""
        ),
        invoice_id=data.invoice_id,
    )
    return replace(entry, **changes)


def test_calculated_result_creates_immutable_credit() -> None:
    result = evaluate(posting_input())

    assert result.status is LedgerPostingStatus.POSTED
    assert isinstance(result.entry, LedgerEntry)
    assert result.entry.entry_type is LedgerEntryType.CREDIT
    assert result.entry.amount == Decimal("119.90")
    assert result.entry.currency is Currency.BRL
    assert result.entry.posted_at == POSTED_AT
    assert result.entry.event_id == "event:1"


def test_entry_id_is_deterministic() -> None:
    first = evaluate(posting_input())
    second = evaluate(posting_input())

    assert first == second
    assert first.entry is not None
    assert first.entry.entry_id == "ledger.remuneration.credit:event:1"


def test_empty_history_allows_posting() -> None:
    result = evaluate(posting_input(existing_entries=()))

    assert result.status is LedgerPostingStatus.POSTED


def test_compatible_existing_credit_is_idempotent() -> None:
    source_ids = tuple(reversed(posting_input().source_reference_ids))
    existing = existing_entry(source_reference_ids=source_ids)

    result = evaluate(posting_input(existing_entries=(existing,)))

    assert result.status is LedgerPostingStatus.ALREADY_POSTED
    assert result.entry is None
    assert result.matching_existing_entry_id == existing.entry_id
    assert result.reasons == (LedgerPostingReason.EVENT_ALREADY_POSTED,)


@pytest.mark.parametrize(
    "existing_changes",
    [
        {"beneficiary_id": "employee:99"},
        {"amount": Decimal("99.90")},
        {"currency": Currency.USD},
        {"posting_reference": "posting:other"},
        {"source_reference_ids": ("source:other",)},
    ],
)
def test_incompatible_existing_credit_requires_review(
    existing_changes: dict[str, object],
) -> None:
    existing = existing_entry(**existing_changes)

    result = evaluate(posting_input(existing_entries=(existing,)))

    assert result.status is LedgerPostingStatus.PENDING_MANUAL_REVIEW
    assert result.reasons == (LedgerPostingReason.LEDGER_REFERENCE_CONFLICT,)
    assert result.entry is None


def test_multiple_existing_credits_for_event_require_review() -> None:
    entries = (
        existing_entry(entry_id="entry:1"),
        existing_entry(entry_id="entry:2"),
    )

    result = evaluate(posting_input(existing_entries=entries))

    assert result.status is LedgerPostingStatus.PENDING_MANUAL_REVIEW
    assert result.reasons == (LedgerPostingReason.DUPLICATE_EVENT_CREDIT,)


def test_distinct_events_can_share_invoice() -> None:
    other = existing_entry(
        entry_id="ledger.remuneration.credit:event:2",
        event_id="event:2",
        invoice_id="invoice:10",
    )

    result = evaluate(posting_input(existing_entries=(other,)))

    assert result.status is LedgerPostingStatus.POSTED
    assert result.entry is not None
    assert result.entry.invoice_id == other.invoice_id
    assert result.entry.event_id != other.event_id


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"beneficiary_id": None}, LedgerPostingReason.MISSING_BENEFICIARY),
        ({"posting_reference": None}, LedgerPostingReason.MISSING_SOURCE_REFERENCE),
        ({"posted_at": None}, LedgerPostingReason.MISSING_POSTED_AT),
        ({"source_reference_ids": ()}, LedgerPostingReason.MISSING_SOURCE_REFERENCE),
    ],
)
def test_missing_required_data_is_not_evaluable(
    changes: dict[str, object], reason: LedgerPostingReason
) -> None:
    result = evaluate(posting_input(**changes))

    assert result.status is LedgerPostingStatus.NOT_EVALUABLE
    assert result.reasons == (reason,)
    assert result.entry is None


def test_naive_posted_at_is_inconsistent() -> None:
    result = evaluate(posting_input(posted_at=datetime(2026, 7, 20, 12)))

    assert result.status is LedgerPostingStatus.NOT_EVALUABLE
    assert result.reasons == (LedgerPostingReason.INCONSISTENT_INPUT,)


@pytest.mark.parametrize(
    "amount",
    [None, Decimal("0"), Decimal("-1"), Decimal("NaN"), 119.90],
)
def test_invalid_amount_never_creates_credit(amount: object) -> None:
    result = evaluate(
        posting_input(remuneration_amount_result=amount_result(amount=amount))
    )

    assert result.status is LedgerPostingStatus.NOT_EVALUABLE
    assert result.reasons == (LedgerPostingReason.INVALID_AMOUNT,)
    assert result.entry is None


@pytest.mark.parametrize(
    ("source_status", "expected_status", "reason"),
    [
        (
            RemunerationAmountStatus.NOT_APPLICABLE,
            LedgerPostingStatus.NOT_APPLICABLE,
            LedgerPostingReason.REMUNERATION_NOT_CALCULATED,
        ),
        (
            RemunerationAmountStatus.NOT_EVALUABLE,
            LedgerPostingStatus.NOT_EVALUABLE,
            LedgerPostingReason.SOURCE_NOT_EVALUABLE,
        ),
        (
            RemunerationAmountStatus.PENDING_MANUAL_REVIEW,
            LedgerPostingStatus.PENDING_MANUAL_REVIEW,
            LedgerPostingReason.SOURCE_PENDING_MANUAL_REVIEW,
        ),
    ],
)
def test_source_status_prevents_posting(
    source_status: RemunerationAmountStatus,
    expected_status: LedgerPostingStatus,
    reason: LedgerPostingReason,
) -> None:
    result = evaluate(
        posting_input(remuneration_amount_result=amount_result(source_status))
    )

    assert result.status is expected_status
    assert result.reasons == (reason,)
    assert result.entry is None


def test_divergent_event_id_is_inconsistent() -> None:
    result = evaluate(
        posting_input(remuneration_amount_result=amount_result(event_id="event:2"))
    )

    assert result.status is LedgerPostingStatus.NOT_EVALUABLE
    assert result.reasons == (LedgerPostingReason.INCONSISTENT_INPUT,)


def test_explicit_ledger_conflict_requires_review() -> None:
    result = evaluate(posting_input(has_ledger_reference_conflict=True))

    assert result.status is LedgerPostingStatus.PENDING_MANUAL_REVIEW
    assert result.reasons == (LedgerPostingReason.LEDGER_REFERENCE_CONFLICT,)


def test_input_history_and_result_are_not_mutated() -> None:
    data = posting_input(existing_entries=(existing_entry(event_id="event:2"),))
    snapshot = deepcopy(data)
    evaluator = RemunerationLedgerPostingEvaluator()

    first = evaluator.evaluate(data)
    second = evaluator.evaluate(data)

    assert first == second
    assert data == snapshot


def test_contracts_are_immutable_and_have_no_balance_field() -> None:
    data = posting_input()
    result = evaluate(data)

    assert "balance" not in {field.name for field in fields(LedgerEntry)}
    assert "balance" not in {field.name for field in fields(LedgerPostingResult)}
    assert result.entry is not None
    with pytest.raises(AttributeError):
        result.entry.amount = Decimal("1")  # type: ignore[misc]
    with pytest.raises(AttributeError):
        data.event_id = "other"  # type: ignore[misc]


def test_implementation_has_no_infrastructure_dependency() -> None:
    source = getsource(ledger_module).lower()

    assert "fastapi" not in source
    assert "sqlalchemy" not in source
    assert "database" not in source
