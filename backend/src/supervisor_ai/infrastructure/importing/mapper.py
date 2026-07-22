from datetime import UTC, date
from decimal import Decimal
from uuid import UUID

from supervisor_ai.application import (
    CommercialEvent,
    FinancialSnapshot,
    PaymentFacts,
    RemunerationFacts,
    RemunerationPostingFacts,
)
from supervisor_ai.application.use_cases import (
    ProcessAndPersistCommercialEventCommand,
)
from supervisor_ai.infrastructure.importing.schema import (
    ValidatedEvidenceDocument,
    ValidatedImportDocument,
    parse_datetime,
)
from supervisor_ai.rules_engine import (
    ContractualEvidenceName,
    EvaluationContext,
    Evidence,
    EvidenceValue,
    OperationalFactName,
)


class JsonImportDocumentMapper:
    def map(
        self, document: ValidatedImportDocument
    ) -> ProcessAndPersistCommercialEventCommand:
        occurred_at = parse_datetime(
            document.event.occurred_at, "event.occurred_at"
        ).astimezone(UTC)
        received_at = parse_datetime(
            document.event.received_at, "event.received_at"
        ).astimezone(UTC)
        event = CommercialEvent(
            id=document.event.id,
            external_reference=document.event.external_reference,
            source=document.event.source,
            occurred_at=occurred_at,
            received_at=received_at,
            raw_payload=document.event.raw_payload,
            created_at=received_at,
        )
        evaluation = EvaluationContext(
            evaluation_id=UUID(document.evaluation.evaluation_id),
            subject_id=document.evaluation.subject_id,
            observed_at=parse_datetime(
                document.evaluation.observed_at, "evaluation.observed_at"
            ).astimezone(UTC),
            evidence=tuple(
                self._evidence(item) for item in document.evaluation.evidence
            ),
        )
        return ProcessAndPersistCommercialEventCommand(
            event=event,
            evaluation_context=evaluation,
            rules_engine_version=document.rules_engine_version,
            financial_snapshot=(
                None
                if document.financial_snapshot is None
                else self._financial_snapshot(document)
            ),
        )

    @staticmethod
    def _financial_snapshot(
        document: ValidatedImportDocument,
    ) -> FinancialSnapshot:
        snapshot = document.financial_snapshot
        if snapshot is None:
            raise TypeError("validated financial snapshot is required")
        payment = snapshot.payment
        remuneration = snapshot.remuneration
        posting = snapshot.posting
        return FinancialSnapshot(
            payment=PaymentFacts(
                evaluated_at=parse_datetime(
                    payment.evaluated_at,
                    "financial_snapshot.payment.evaluated_at",
                ).astimezone(UTC),
                invoice_id=payment.invoice_id,
                invoice_due_date=(
                    None
                    if payment.invoice_due_date is None
                    else date.fromisoformat(payment.invoice_due_date)
                ),
                invoice_paid_at=(
                    None
                    if payment.invoice_paid_at is None
                    else parse_datetime(
                        payment.invoice_paid_at,
                        "financial_snapshot.payment.invoice_paid_at",
                    ).astimezone(UTC)
                ),
                invoice_status=payment.invoice_status,
                invoice_recurring_amount=_decimal(
                    payment.invoice_recurring_amount
                ),
                expected_recurring_amount=_decimal(
                    payment.expected_recurring_amount
                ),
                invoice_linked_to_event=payment.invoice_linked_to_event,
                is_first_new_value_invoice=payment.is_first_new_value_invoice,
                first_invoice_candidate_count=(
                    payment.first_invoice_candidate_count
                ),
                already_validated_event_ids=(
                    payment.already_validated_event_ids
                ),
                financial_reference_ids=payment.financial_reference_ids,
                has_link_conflict=payment.has_link_conflict,
                has_duplicate_invoice_event_link=(
                    payment.has_duplicate_invoice_event_link
                ),
                has_inconsistent_financial_input=(
                    payment.has_inconsistent_financial_input
                ),
            ),
            remuneration=RemunerationFacts(
                payment_validation_reference=(
                    remuneration.payment_validation_reference
                ),
                previous_recurring_amount=_decimal(
                    remuneration.previous_recurring_amount
                ),
                new_recurring_amount=_decimal(
                    remuneration.new_recurring_amount
                ),
                full_new_plan_amount=_decimal(remuneration.full_new_plan_amount),
                additional_type=remuneration.additional_type,
                renews_loyalty=remuneration.renews_loyalty,
                commercial_reference_ids=remuneration.commercial_reference_ids,
                calculation_reference_ids=remuneration.calculation_reference_ids,
                has_commercial_classification_conflict=(
                    remuneration.has_commercial_classification_conflict
                ),
                has_inconsistent_input=remuneration.has_inconsistent_input,
            ),
            posting=RemunerationPostingFacts(
                beneficiary_id=posting.beneficiary_id,
                posted_at=(
                    None
                    if posting.posted_at is None
                    else parse_datetime(
                        posting.posted_at,
                        "financial_snapshot.posting.posted_at",
                    ).astimezone(UTC)
                ),
                posting_reference=posting.posting_reference,
                source_reference_ids=posting.source_reference_ids,
                remuneration_calculation_reference=(
                    posting.remuneration_calculation_reference
                ),
                has_ledger_reference_conflict=(
                    posting.has_ledger_reference_conflict
                ),
                has_inconsistent_input=posting.has_inconsistent_input,
            ),
        )

    @staticmethod
    def _evidence(document: ValidatedEvidenceDocument) -> Evidence:
        return Evidence(
            evidence_id=document.id,
            name=document.name,
            value=_map_evidence_value(document.name, document.value),
            observed_at=parse_datetime(
                document.observed_at, "evaluation.evidence.observed_at"
            ).astimezone(UTC),
        )


def _map_evidence_value(
    name: ContractualEvidenceName | OperationalFactName,
    value: object,
) -> EvidenceValue:
    if name in {
        ContractualEvidenceName.PREVIOUS_ADDITIONALS,
        ContractualEvidenceName.CURRENT_ADDITIONALS,
    }:
        if not isinstance(value, list):
            raise TypeError("validated additional evidence must be an array")
        return tuple(value)
    if name in {
        ContractualEvidenceName.PREVIOUS_RECURRING_VALUE,
        ContractualEvidenceName.CURRENT_RECURRING_VALUE,
    }:
        if type(value) not in {str, int, float}:
            raise TypeError("validated monetary evidence must be decimal-compatible")
        return Decimal(str(value))
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return value
    if isinstance(value, list):
        return tuple(_map_generic_evidence_value(item) for item in value)
    raise TypeError("validated evidence has no domain mapping")


def _map_generic_evidence_value(value: object) -> EvidenceValue:
    if value is None:
        return None
    if isinstance(value, bool | str | int | float):
        return value
    if isinstance(value, list):
        return tuple(_map_generic_evidence_value(item) for item in value)
    raise TypeError("validated operational evidence has no domain mapping")


def _decimal(value: str | None) -> Decimal | None:
    return None if value is None else Decimal(value)
