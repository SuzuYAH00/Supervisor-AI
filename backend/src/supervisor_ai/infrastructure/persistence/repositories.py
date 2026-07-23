from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy import Select, and_, or_, select
from sqlalchemy.orm import Session

from supervisor_ai.application.persistence import (
    CommercialEvent,
    CommercialEventCursorPosition,
    ProcessingRun,
)
from supervisor_ai.infrastructure.persistence.mappings import (
    event_to_record,
    ledger_entry_to_record,
    processing_run_to_record,
    record_to_event,
    record_to_ledger_entry,
    record_to_processing_run,
)
from supervisor_ai.infrastructure.persistence.models import (
    CommercialEventRecord,
    LedgerEntryRecord,
    ProcessingRunRecord,
)
from supervisor_ai.rules_engine import LedgerEntry, LedgerEntryType


class SqlAlchemyEventRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, event: CommercialEvent) -> None:
        self.session.add(event_to_record(event))
        self.session.flush()

    def get_by_id(self, event_id: str) -> CommercialEvent | None:
        record = self.session.get(CommercialEventRecord, event_id)
        return None if record is None else record_to_event(record)

    def get_by_external_reference(
        self, external_reference: str
    ) -> CommercialEvent | None:
        record = self.session.scalar(
            select(CommercialEventRecord).where(
                CommercialEventRecord.external_reference == external_reference
            )
        )
        return None if record is None else record_to_event(record)

    def search(
        self,
        *,
        source: str | None,
        external_reference: str | None,
        start_date: date | None,
        end_date: date | None,
        after: CommercialEventCursorPosition | None,
        limit: int,
    ) -> tuple[CommercialEvent, ...]:
        statement = select(CommercialEventRecord)
        if source is not None:
            statement = statement.where(CommercialEventRecord.source == source)
        if external_reference is not None:
            statement = statement.where(
                CommercialEventRecord.external_reference == external_reference
            )
        if start_date is not None:
            statement = statement.where(
                CommercialEventRecord.occurred_at
                >= datetime.combine(start_date, time.min, tzinfo=UTC)
            )
        if end_date is not None:
            end_boundary = (
                datetime.combine(end_date, time.max, tzinfo=UTC)
                if end_date == date.max
                else datetime.combine(
                    end_date + timedelta(days=1), time.min, tzinfo=UTC
                )
            )
            comparison = (
                CommercialEventRecord.occurred_at <= end_boundary
                if end_date == date.max
                else CommercialEventRecord.occurred_at < end_boundary
            )
            statement = statement.where(comparison)
        if after is not None:
            statement = statement.where(
                or_(
                    CommercialEventRecord.occurred_at < after.occurred_at,
                    and_(
                        CommercialEventRecord.occurred_at == after.occurred_at,
                        CommercialEventRecord.id < after.event_id,
                    ),
                )
            )
        records = self.session.scalars(
            statement.order_by(
                CommercialEventRecord.occurred_at.desc(),
                CommercialEventRecord.id.desc(),
            ).limit(limit)
        )
        return tuple(record_to_event(record) for record in records)


class SqlAlchemyProcessingRunRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, run: ProcessingRun) -> None:
        self.session.add(processing_run_to_record(run))
        self.session.flush()

    def get_by_id(self, run_id: str) -> ProcessingRun | None:
        record = self.session.get(ProcessingRunRecord, run_id)
        return None if record is None else record_to_processing_run(record)

    def find_by_event_id(self, event_id: str) -> tuple[ProcessingRun, ...]:
        records = self.session.scalars(
            select(ProcessingRunRecord)
            .where(ProcessingRunRecord.event_id == event_id)
            .order_by(ProcessingRunRecord.started_at, ProcessingRunRecord.id)
        )
        return tuple(record_to_processing_run(record) for record in records)


class SqlAlchemyLedgerRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, entry: LedgerEntry) -> None:
        self.session.add(ledger_entry_to_record(entry))
        self.session.flush()

    def get_by_entry_id(self, entry_id: str) -> LedgerEntry | None:
        record = self.session.get(LedgerEntryRecord, entry_id)
        return None if record is None else record_to_ledger_entry(record)

    def find_credit_by_event_id(self, event_id: str) -> LedgerEntry | None:
        record = self.session.scalar(
            select(LedgerEntryRecord).where(
                LedgerEntryRecord.event_id == event_id,
                LedgerEntryRecord.entry_type == LedgerEntryType.CREDIT.value,
            )
        )
        return None if record is None else record_to_ledger_entry(record)

    def find_by_event_id(self, event_id: str) -> tuple[LedgerEntry, ...]:
        records = self.session.scalars(
            select(LedgerEntryRecord)
            .where(LedgerEntryRecord.event_id == event_id)
            .order_by(LedgerEntryRecord.posted_at, LedgerEntryRecord.entry_id)
        )
        return tuple(record_to_ledger_entry(record) for record in records)

    def find_credits(
        self,
        *,
        beneficiary_id: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> tuple[LedgerEntry, ...]:
        statement = select(LedgerEntryRecord).where(
            LedgerEntryRecord.entry_type == LedgerEntryType.CREDIT.value
        )
        statement = _apply_credit_filters(
            statement,
            beneficiary_id=beneficiary_id,
            start_date=start_date,
            end_date=end_date,
        ).order_by(LedgerEntryRecord.posted_at, LedgerEntryRecord.entry_id)
        records = self.session.scalars(statement)
        return tuple(record_to_ledger_entry(record) for record in records)


def _apply_credit_filters(
    statement: Select[tuple[LedgerEntryRecord]],
    *,
    beneficiary_id: str | None,
    start_date: date | None,
    end_date: date | None,
) -> Select[tuple[LedgerEntryRecord]]:
    if beneficiary_id is not None:
        statement = statement.where(
            LedgerEntryRecord.beneficiary_id == beneficiary_id
        )
    if start_date is not None:
        statement = statement.where(
            LedgerEntryRecord.posted_at
            >= datetime.combine(start_date, time.min, tzinfo=UTC)
        )
    if end_date is not None:
        if end_date == date.max:
            statement = statement.where(
                LedgerEntryRecord.posted_at
                <= datetime.combine(end_date, time.max, tzinfo=UTC)
            )
        else:
            statement = statement.where(
                LedgerEntryRecord.posted_at
                < datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=UTC)
            )
    return statement
