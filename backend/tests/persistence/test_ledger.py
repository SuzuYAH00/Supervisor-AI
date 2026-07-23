from dataclasses import replace
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from supervisor_ai.infrastructure.persistence.models import LedgerEntryRecord
from supervisor_ai.infrastructure.persistence.repositories import (
    SqlAlchemyEventRepository,
    SqlAlchemyLedgerRepository,
)
from supervisor_ai.rules_engine import LedgerEntry
from tests.persistence.factories import commercial_event, ledger_entry


def persist_event(session: Session, event_id: str = "event-1") -> None:
    SqlAlchemyEventRepository(session).add(
        commercial_event(event_id, external_reference=f"external-{event_id}")
    )


def test_saves_and_recovers_domain_ledger_entry_exactly(
    session_factory: sessionmaker[Session],
) -> None:
    expected = ledger_entry(amount=Decimal("119.123456"))
    with session_factory() as session:
        persist_event(session)
        repository = SqlAlchemyLedgerRepository(session)
        repository.add(expected)
        session.commit()
        session.expunge_all()

        recovered = repository.get_by_entry_id(expected.entry_id)
        assert recovered == expected
        assert isinstance(recovered, LedgerEntry)
        assert not isinstance(recovered, LedgerEntryRecord)
        assert repository.find_credit_by_event_id(expected.event_id) == expected


def test_optional_invoice_is_preserved(
    session_factory: sessionmaker[Session],
) -> None:
    expected = ledger_entry(invoice_id=None)
    with session_factory() as session:
        persist_event(session)
        repository = SqlAlchemyLedgerRepository(session)
        repository.add(expected)
        session.commit()
        assert repository.get_by_entry_id(expected.entry_id) == expected


def test_different_events_can_share_invoice(
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory() as session:
        persist_event(session, "event-1")
        persist_event(session, "event-2")
        repository = SqlAlchemyLedgerRepository(session)
        repository.add(ledger_entry("ledger-1", "event-1"))
        repository.add(ledger_entry("ledger-2", "event-2"))
        session.commit()


@pytest.mark.parametrize(
    ("first", "second"),
    [
        (ledger_entry("ledger-1"), ledger_entry("ledger-2")),
        (ledger_entry("ledger-1"), ledger_entry("ledger-1")),
    ],
)
def test_duplicate_credit_or_entry_id_is_rejected(
    session_factory: sessionmaker[Session],
    first: LedgerEntry,
    second: LedgerEntry,
) -> None:
    with session_factory() as session:
        persist_event(session)
        repository = SqlAlchemyLedgerRepository(session)
        repository.add(first)
        with pytest.raises(IntegrityError):
            repository.add(second)


@pytest.mark.parametrize("amount", [Decimal("0"), Decimal("-0.01")])
def test_non_positive_amount_is_rejected(
    session_factory: sessionmaker[Session], amount: Decimal
) -> None:
    with session_factory() as session:
        persist_event(session)
        with pytest.raises(IntegrityError):
            SqlAlchemyLedgerRepository(session).add(ledger_entry(amount=amount))


def test_ledger_has_no_balance_column() -> None:
    assert "balance" not in LedgerEntryRecord.__table__.columns


def test_finds_filtered_credits_in_deterministic_posting_order(
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory() as session:
        for event_id in ("event-1", "event-2", "event-3"):
            persist_event(session, event_id)
        repository = SqlAlchemyLedgerRepository(session)
        repository.add(
            replace(
                ledger_entry("ledger-2", "event-2", amount=Decimal("20.00")),
                beneficiary_id="collaborator-1",
                posted_at=datetime(2026, 7, 20, 14, tzinfo=UTC),
            )
        )
        repository.add(
            replace(
                ledger_entry("ledger-1", "event-1", amount=Decimal("10.00")),
                beneficiary_id="collaborator-1",
                posted_at=datetime(2026, 7, 20, 13, tzinfo=UTC),
            )
        )
        repository.add(
            replace(
                ledger_entry("ledger-3", "event-3", amount=Decimal("30.00")),
                beneficiary_id="collaborator-2",
                posted_at=datetime(2026, 8, 1, 13, tzinfo=UTC),
            )
        )
        session.commit()

        result = repository.find_credits(
            beneficiary_id="collaborator-1",
            start_date=date(2026, 7, 20),
            end_date=date(2026, 7, 20),
        )

    assert tuple(entry.entry_id for entry in result) == ("ledger-1", "ledger-2")
    assert all(entry.beneficiary_id == "collaborator-1" for entry in result)
