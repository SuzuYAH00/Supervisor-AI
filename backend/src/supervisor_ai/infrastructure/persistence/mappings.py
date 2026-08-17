from copy import deepcopy

from supervisor_ai.application.persistence import (
    AttendanceFact,
    CollaboratorExternalIdentity,
    CommercialEvent,
    CsatEvaluation,
    DailyWorkStatusFact,
    OperationalCollaboratorProfile,
    ProcessingRun,
)
from supervisor_ai.infrastructure.persistence.models import (
    AttendanceFactRecord,
    CollaboratorExternalIdentityRecord,
    CommercialEventRecord,
    CsatEvaluationRecord,
    DailyWorkStatusRecord,
    LedgerEntryRecord,
    OperationalCollaboratorProfileRecord,
    ProcessingRunRecord,
)
from supervisor_ai.rules_engine import (
    ClassificationIdentity,
    CsatCompetitiveChannel,
    Currency,
    LedgerEntry,
    LedgerEntryType,
)


def event_to_record(event: CommercialEvent) -> CommercialEventRecord:
    return CommercialEventRecord(
        id=event.id,
        external_reference=event.external_reference,
        source=event.source,
        occurred_at=event.occurred_at,
        received_at=event.received_at,
        raw_payload=deepcopy(event.raw_payload),
        created_at=event.created_at,
    )


def record_to_event(record: CommercialEventRecord) -> CommercialEvent:
    return CommercialEvent(
        id=record.id,
        external_reference=record.external_reference,
        source=record.source,
        occurred_at=record.occurred_at,
        received_at=record.received_at,
        raw_payload=deepcopy(record.raw_payload),
        created_at=record.created_at,
    )


def csat_evaluation_to_record(
    evaluation: CsatEvaluation,
) -> CsatEvaluationRecord:
    return CsatEvaluationRecord(
        id=evaluation.id,
        external_reference=evaluation.external_reference,
        source=evaluation.source,
        collaborator_id=evaluation.collaborator_id,
        channel=evaluation.channel,
        score=evaluation.score,
        evaluated_at=evaluation.evaluated_at,
        created_at=evaluation.created_at,
    )


def record_to_csat_evaluation(record: CsatEvaluationRecord) -> CsatEvaluation:
    return CsatEvaluation(
        id=record.id,
        external_reference=record.external_reference,
        source=record.source,
        collaborator_id=record.collaborator_id,
        channel=record.channel,
        score=record.score,
        evaluated_at=record.evaluated_at,
        created_at=record.created_at,
    )


def operational_collaborator_profile_to_record(
    profile: OperationalCollaboratorProfile,
) -> OperationalCollaboratorProfileRecord:
    return OperationalCollaboratorProfileRecord(
        collaborator_id=profile.collaborator_id,
        competitive_channel=profile.competitive_channel.value,
        created_at=profile.created_at,
    )


def record_to_operational_collaborator_profile(
    record: OperationalCollaboratorProfileRecord,
) -> OperationalCollaboratorProfile:
    return OperationalCollaboratorProfile(
        collaborator_id=record.collaborator_id,
        competitive_channel=CsatCompetitiveChannel(record.competitive_channel),
        created_at=record.created_at,
    )


def collaborator_external_identity_to_record(
    identity: CollaboratorExternalIdentity,
) -> CollaboratorExternalIdentityRecord:
    return CollaboratorExternalIdentityRecord(
        collaborator_id=identity.collaborator_id,
        source=identity.source,
        external_identity=identity.external_identity,
        created_at=identity.created_at,
    )


def record_to_collaborator_external_identity(
    record: CollaboratorExternalIdentityRecord,
) -> CollaboratorExternalIdentity:
    return CollaboratorExternalIdentity(
        collaborator_id=record.collaborator_id,
        source=record.source,
        external_identity=record.external_identity,
        created_at=record.created_at,
    )


def attendance_to_record(attendance: AttendanceFact) -> AttendanceFactRecord:
    return AttendanceFactRecord(
        id=attendance.id,
        external_reference=attendance.external_reference,
        source=attendance.source,
        customer_code=attendance.customer_code,
        operator_id=attendance.operator_id,
        channel=attendance.channel,
        occurred_at=attendance.occurred_at,
        process_code=attendance.process.code,
        process_description=attendance.process.description,
        opening_code=attendance.opening_classification.code,
        opening_description=attendance.opening_classification.description,
        closing_code=attendance.closing_classification.code,
        closing_description=attendance.closing_classification.description,
        created_at=attendance.created_at,
    )


def record_to_attendance(record: AttendanceFactRecord) -> AttendanceFact:
    return AttendanceFact(
        id=record.id,
        external_reference=record.external_reference,
        source=record.source,
        customer_code=record.customer_code,
        operator_id=record.operator_id,
        channel=record.channel,
        occurred_at=record.occurred_at,
        process=ClassificationIdentity(
            record.process_code, record.process_description
        ),
        opening_classification=ClassificationIdentity(
            record.opening_code, record.opening_description
        ),
        closing_classification=ClassificationIdentity(
            record.closing_code, record.closing_description
        ),
        created_at=record.created_at,
    )


def daily_work_status_to_record(
    fact: DailyWorkStatusFact,
) -> DailyWorkStatusRecord:
    return DailyWorkStatusRecord(
        id=fact.id,
        collaborator_id=fact.collaborator_id,
        work_date=fact.work_date,
        competence_month=fact.competence_month,
        raw_code=fact.raw_code,
        source=fact.source,
        external_reference=fact.external_reference,
        source_sheet=fact.source_sheet,
        source_cell=fact.source_cell,
        created_at=fact.created_at,
    )


def record_to_daily_work_status(
    record: DailyWorkStatusRecord,
) -> DailyWorkStatusFact:
    return DailyWorkStatusFact(
        id=record.id,
        collaborator_id=record.collaborator_id,
        work_date=record.work_date,
        competence_month=record.competence_month,
        raw_code=record.raw_code,
        source=record.source,
        external_reference=record.external_reference,
        source_sheet=record.source_sheet,
        source_cell=record.source_cell,
        created_at=record.created_at,
    )


def processing_run_to_record(run: ProcessingRun) -> ProcessingRunRecord:
    return ProcessingRunRecord(
        id=run.id,
        event_id=run.event_id,
        final_status=run.final_status,
        started_at=run.started_at,
        completed_at=run.completed_at,
        rules_engine_version=run.rules_engine_version,
        phase_results=deepcopy(run.phase_results),
        warnings=deepcopy(run.warnings),
        audit_references=deepcopy(run.audit_references),
        created_at=run.created_at,
    )


def record_to_processing_run(record: ProcessingRunRecord) -> ProcessingRun:
    return ProcessingRun(
        id=record.id,
        event_id=record.event_id,
        final_status=record.final_status,
        started_at=record.started_at,
        completed_at=record.completed_at,
        rules_engine_version=record.rules_engine_version,
        phase_results=deepcopy(record.phase_results),
        warnings=deepcopy(record.warnings),
        audit_references=deepcopy(record.audit_references),
        created_at=record.created_at,
    )


def ledger_entry_to_record(entry: LedgerEntry) -> LedgerEntryRecord:
    return LedgerEntryRecord(
        entry_id=entry.entry_id,
        event_id=entry.event_id,
        beneficiary_id=entry.beneficiary_id,
        entry_type=entry.entry_type.value,
        amount=entry.amount,
        currency=entry.currency.value,
        posted_at=entry.posted_at,
        posting_reference=entry.posting_reference,
        source_reference_ids=list(entry.source_reference_ids),
        remuneration_calculation_reference=(
            entry.remuneration_calculation_reference
        ),
        invoice_id=entry.invoice_id,
    )


def record_to_ledger_entry(record: LedgerEntryRecord) -> LedgerEntry:
    return LedgerEntry(
        entry_id=record.entry_id,
        event_id=record.event_id,
        beneficiary_id=record.beneficiary_id,
        entry_type=LedgerEntryType(record.entry_type),
        amount=record.amount,
        currency=Currency(record.currency),
        posted_at=record.posted_at,
        posting_reference=record.posting_reference,
        source_reference_ids=tuple(record.source_reference_ids),
        remuneration_calculation_reference=(
            record.remuneration_calculation_reference
        ),
        invoice_id=record.invoice_id,
    )
