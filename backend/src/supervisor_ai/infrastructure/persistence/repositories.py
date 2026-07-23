from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy import Select, and_, case, distinct, func, or_, select
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from supervisor_ai.application.persistence import (
    CollaboratorFinancialTimelineCursorPosition,
    CollaboratorFinancialTimelineRecord,
    CommercialEvent,
    CommercialEventCursorPosition,
    ProcessingHealthCount,
    ProcessingHealthRecord,
    ProcessingRun,
    ProcessingRunCursorPosition,
    ProcessingRunListRecord,
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
from supervisor_ai.rules_engine import Currency, LedgerEntry, LedgerEntryType


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

    def search(
        self,
        *,
        source: str | None,
        external_reference: str | None,
        final_status: str | None,
        rules_engine_version: str | None,
        start_date: date | None,
        end_date: date | None,
        after: ProcessingRunCursorPosition | None,
        limit: int,
    ) -> tuple[ProcessingRunListRecord, ...]:
        statement = select(
            ProcessingRunRecord.id,
            ProcessingRunRecord.event_id,
            CommercialEventRecord.source,
            CommercialEventRecord.external_reference,
            ProcessingRunRecord.started_at,
            ProcessingRunRecord.completed_at,
            ProcessingRunRecord.final_status,
            ProcessingRunRecord.rules_engine_version,
        ).join(
            CommercialEventRecord,
            CommercialEventRecord.id == ProcessingRunRecord.event_id,
        )
        statement = statement.where(
            *_processing_run_filters(
                start_date=start_date,
                end_date=end_date,
                source=source,
                rules_engine_version=rules_engine_version,
            )
        )
        if external_reference is not None:
            statement = statement.where(
                CommercialEventRecord.external_reference == external_reference
            )
        if final_status is not None:
            statement = statement.where(
                ProcessingRunRecord.final_status == final_status
            )
        if after is not None:
            statement = statement.where(
                or_(
                    ProcessingRunRecord.started_at < after.started_at,
                    and_(
                        ProcessingRunRecord.started_at == after.started_at,
                        ProcessingRunRecord.id < after.processing_run_id,
                    ),
                )
            )
        rows = self.session.execute(
            statement.order_by(
                ProcessingRunRecord.started_at.desc(),
                ProcessingRunRecord.id.desc(),
            ).limit(limit)
        )
        return tuple(
            ProcessingRunListRecord(
                processing_run_id=row.id,
                event_id=row.event_id,
                source=row.source,
                external_reference=row.external_reference,
                started_at=row.started_at,
                completed_at=row.completed_at,
                final_status=row.final_status,
                rules_engine_version=row.rules_engine_version,
            )
            for row in rows
        )


class SqlAlchemyProcessingHealthRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_processing_health(
        self,
        *,
        start_date: date | None,
        end_date: date | None,
        source: str | None,
        rules_engine_version: str | None,
    ) -> ProcessingHealthRecord:
        run_filters = _processing_run_filters(
            start_date=start_date,
            end_date=end_date,
            source=source,
            rules_engine_version=rules_engine_version,
        )
        run_source = (
            select(
                ProcessingRunRecord.event_id.label("event_id"),
                ProcessingRunRecord.final_status.label("final_status"),
                ProcessingRunRecord.rules_engine_version.label(
                    "rules_engine_version"
                ),
            )
            .join(
                CommercialEventRecord,
                CommercialEventRecord.id == ProcessingRunRecord.event_id,
            )
            .where(*run_filters)
            .subquery()
        )
        total = self.session.scalar(select(func.count()).select_from(run_source)) or 0
        status_rows = self.session.execute(
            select(run_source.c.final_status, func.count())
            .group_by(run_source.c.final_status)
            .order_by(run_source.c.final_status)
        ).all()
        version_rows = self.session.execute(
            select(run_source.c.rules_engine_version, func.count())
            .group_by(run_source.c.rules_engine_version)
            .order_by(run_source.c.rules_engine_version)
        ).all()

        has_processing_filter = (
            start_date is not None
            or end_date is not None
            or rules_engine_version is not None
        )
        if has_processing_filter:
            cohort = select(
                distinct(run_source.c.event_id).label("event_id")
            ).subquery()
        else:
            cohort_statement = select(
                CommercialEventRecord.id.label("event_id")
            )
            if source is not None:
                cohort_statement = cohort_statement.where(
                    CommercialEventRecord.source == source
                )
            cohort = cohort_statement.subquery()

        run_counts = (
            select(
                run_source.c.event_id,
                func.count().label("run_count"),
            )
            .group_by(run_source.c.event_id)
            .subquery()
        )
        ledger_events = (
            select(LedgerEntryRecord.event_id.label("event_id"))
            .group_by(LedgerEntryRecord.event_id)
            .subquery()
        )
        metrics = self.session.execute(
            select(
                func.count(cohort.c.event_id),
                func.count(run_counts.c.event_id),
                func.coalesce(
                    func.sum(case((run_counts.c.run_count > 1, 1), else_=0)),
                    0,
                ),
                func.count(ledger_events.c.event_id),
            )
            .select_from(cohort)
            .outerjoin(
                run_counts,
                run_counts.c.event_id == cohort.c.event_id,
            )
            .outerjoin(
                ledger_events,
                ledger_events.c.event_id == cohort.c.event_id,
            )
        ).one()
        event_total = int(metrics[0])
        with_runs = int(metrics[1])
        with_ledger = int(metrics[3])
        return ProcessingHealthRecord(
            processing_run_total=int(total),
            by_final_status=tuple(
                ProcessingHealthCount(str(value), int(count))
                for value, count in status_rows
            ),
            by_rules_engine_version=tuple(
                ProcessingHealthCount(str(value), int(count))
                for value, count in version_rows
            ),
            events_with_processing_runs=with_runs,
            events_without_processing_runs=event_total - with_runs,
            events_with_multiple_processing_runs=int(metrics[2]),
            events_with_ledger_entries=with_ledger,
            events_without_ledger_entries=event_total - with_ledger,
        )


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

    def search_collaborator_timeline(
        self,
        *,
        collaborator_id: str,
        start_date: date | None,
        end_date: date | None,
        entry_type: LedgerEntryType | None,
        currency: Currency | None,
        after: CollaboratorFinancialTimelineCursorPosition | None,
        limit: int,
    ) -> tuple[CollaboratorFinancialTimelineRecord, ...]:
        statement = (
            select(
                LedgerEntryRecord.entry_id,
                LedgerEntryRecord.posted_at,
                LedgerEntryRecord.entry_type,
                LedgerEntryRecord.amount,
                LedgerEntryRecord.currency,
                LedgerEntryRecord.invoice_id,
                LedgerEntryRecord.posting_reference,
                LedgerEntryRecord.remuneration_calculation_reference,
                LedgerEntryRecord.source_reference_ids,
                CommercialEventRecord.id,
                CommercialEventRecord.external_reference,
                CommercialEventRecord.source,
                CommercialEventRecord.occurred_at,
            )
            .join(
                CommercialEventRecord,
                CommercialEventRecord.id == LedgerEntryRecord.event_id,
            )
            .where(LedgerEntryRecord.beneficiary_id == collaborator_id)
        )
        if start_date is not None:
            statement = statement.where(
                LedgerEntryRecord.posted_at
                >= datetime.combine(start_date, time.min, tzinfo=UTC)
            )
        if end_date is not None:
            statement = statement.where(
                LedgerEntryRecord.posted_at
                <= datetime.combine(end_date, time.max, tzinfo=UTC)
                if end_date == date.max
                else LedgerEntryRecord.posted_at
                < datetime.combine(
                    end_date + timedelta(days=1), time.min, tzinfo=UTC
                )
            )
        if entry_type is not None:
            statement = statement.where(
                LedgerEntryRecord.entry_type == entry_type.value
            )
        if currency is not None:
            statement = statement.where(LedgerEntryRecord.currency == currency.value)
        if after is not None:
            statement = statement.where(
                or_(
                    LedgerEntryRecord.posted_at < after.posted_at,
                    and_(
                        LedgerEntryRecord.posted_at == after.posted_at,
                        LedgerEntryRecord.entry_id < after.ledger_entry_id,
                    ),
                )
            )
        rows = self.session.execute(
            statement.order_by(
                LedgerEntryRecord.posted_at.desc(),
                LedgerEntryRecord.entry_id.desc(),
            ).limit(limit)
        ).all()
        return tuple(
            CollaboratorFinancialTimelineRecord(
                ledger_entry_id=row.entry_id,
                posted_at=row.posted_at,
                entry_type=LedgerEntryType(row.entry_type),
                amount=row.amount,
                currency=Currency(row.currency),
                invoice_id=row.invoice_id,
                posting_reference=row.posting_reference,
                remuneration_calculation_reference=(
                    row.remuneration_calculation_reference
                ),
                source_reference_ids=tuple(row.source_reference_ids),
                event_id=row.id,
                external_reference=row.external_reference,
                event_source=row.source,
                event_occurred_at=row.occurred_at,
            )
            for row in rows
        )


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


def _processing_run_filters(
    *,
    start_date: date | None,
    end_date: date | None,
    source: str | None,
    rules_engine_version: str | None,
) -> tuple[ColumnElement[bool], ...]:
    filters: list[ColumnElement[bool]] = []
    if start_date is not None:
        filters.append(
            ProcessingRunRecord.started_at
            >= datetime.combine(start_date, time.min, tzinfo=UTC)
        )
    if end_date is not None:
        filters.append(
            ProcessingRunRecord.started_at
            <= datetime.combine(end_date, time.max, tzinfo=UTC)
            if end_date == date.max
            else ProcessingRunRecord.started_at
            < datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=UTC)
        )
    if source is not None:
        filters.append(CommercialEventRecord.source == source)
    if rules_engine_version is not None:
        filters.append(
            ProcessingRunRecord.rules_engine_version == rules_engine_version
        )
    return tuple(filters)
