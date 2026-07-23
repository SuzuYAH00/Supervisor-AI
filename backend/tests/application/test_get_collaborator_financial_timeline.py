from datetime import UTC, date, datetime
from decimal import Decimal
from types import TracebackType

import pytest

from supervisor_ai.application import (
    CollaboratorFinancialTimelineCursorPosition,
    CollaboratorFinancialTimelineRecord,
)
from supervisor_ai.application.use_cases import (
    GetCollaboratorFinancialTimelineQuery,
    GetCollaboratorFinancialTimelineUseCase,
)
from supervisor_ai.rules_engine import Currency, LedgerEntryType

NOW = datetime(2026, 7, 22, 12, tzinfo=UTC)


def record(index: int) -> CollaboratorFinancialTimelineRecord:
    return CollaboratorFinancialTimelineRecord(
        ledger_entry_id=f"ledger-{index}",
        posted_at=NOW,
        entry_type=(
            LedgerEntryType.CREDIT if index % 2 else LedgerEntryType.ADJUSTMENT
        ),
        amount=Decimal(f"{index}.10"),
        currency=Currency.BRL,
        invoice_id=f"invoice-{index}",
        posting_reference=f"posting-{index}",
        remuneration_calculation_reference=f"calculation-{index}",
        source_reference_ids=(f"source-{index}",),
        event_id=f"event-{index}",
        external_reference=f"external-{index}",
        event_source="csv",
        event_occurred_at=NOW,
    )


class LedgerRepositoryFake:
    def __init__(self, records=(), error: Exception | None = None) -> None:
        self.records = records
        self.error = error
        self.arguments: dict[str, object] = {}

    def search_collaborator_timeline(self, **arguments):
        self.arguments = arguments
        if self.error is not None:
            raise self.error
        return self.records


class UnitOfWorkFake:
    def __init__(self, ledger: LedgerRepositoryFake) -> None:
        self.ledger = ledger
        self.closed = False
        self.rolled_back = False
        self.commits = 0

    def __enter__(self):
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        del exc_value, traceback
        self.closed = True
        self.rolled_back = exc_type is not None

    def commit(self) -> None:
        self.commits += 1


def test_empty_timeline_uses_defaults_and_is_read_only() -> None:
    repository = LedgerRepositoryFake()
    unit_of_work = UnitOfWorkFake(repository)
    result = GetCollaboratorFinancialTimelineUseCase(
        lambda: unit_of_work
    ).execute(GetCollaboratorFinancialTimelineQuery("alice"))
    assert result.items == ()
    assert not result.has_more
    assert result.next_cursor_position is None
    assert repository.arguments["limit"] == 51
    assert repository.arguments["collaborator_id"] == "alice"
    assert unit_of_work.closed and unit_of_work.commits == 0


def test_filters_limit_plus_one_projection_and_cursor() -> None:
    records = (record(3), record(2), record(1))
    repository = LedgerRepositoryFake(records)
    unit_of_work = UnitOfWorkFake(repository)
    after = CollaboratorFinancialTimelineCursorPosition(NOW, "ledger-9")
    query = GetCollaboratorFinancialTimelineQuery(
        "alice",
        start_date=date(2026, 7, 1),
        end_date=date(2026, 7, 31),
        entry_type=LedgerEntryType.CREDIT,
        currency=Currency.BRL,
        limit=2,
        after=after,
    )
    result = GetCollaboratorFinancialTimelineUseCase(
        lambda: unit_of_work
    ).execute(query)
    assert repository.arguments == {
        "collaborator_id": "alice",
        "start_date": date(2026, 7, 1),
        "end_date": date(2026, 7, 31),
        "entry_type": LedgerEntryType.CREDIT,
        "currency": Currency.BRL,
        "after": after,
        "limit": 3,
    }
    assert tuple(item.ledger_entry_id for item in result.items) == (
        "ledger-3",
        "ledger-2",
    )
    assert result.items[0].amount == Decimal("3.10")
    assert result.items[0].commercial_event.event_id == "event-3"
    assert result.has_more
    assert result.next_cursor_position == (
        CollaboratorFinancialTimelineCursorPosition(NOW, "ledger-2")
    )
    assert not hasattr(result.items[0].commercial_event, "raw_payload")


@pytest.mark.parametrize(
    "arguments",
    [
        {"collaborator_id": ""},
        {"collaborator_id": "   "},
        {"collaborator_id": "x" * 129},
        {"collaborator_id": "a", "limit": 0},
        {"collaborator_id": "a", "limit": 101},
        {
            "collaborator_id": "a",
            "start_date": date(2026, 8, 1),
            "end_date": date(2026, 7, 31),
        },
    ],
)
def test_query_rejects_invalid_values(arguments) -> None:
    with pytest.raises(ValueError):
        GetCollaboratorFinancialTimelineQuery(**arguments)


@pytest.mark.parametrize("limit", [1, 50, 100])
def test_query_accepts_limit_boundaries(limit: int) -> None:
    assert GetCollaboratorFinancialTimelineQuery("a", limit=limit).limit == limit


def test_failure_rolls_back_context_without_commit() -> None:
    repository = LedgerRepositoryFake(error=RuntimeError("database failed"))
    unit_of_work = UnitOfWorkFake(repository)
    service = GetCollaboratorFinancialTimelineUseCase(lambda: unit_of_work)
    with pytest.raises(RuntimeError):
        service.execute(GetCollaboratorFinancialTimelineQuery("alice"))
    assert unit_of_work.closed and unit_of_work.rolled_back
    assert unit_of_work.commits == 0
