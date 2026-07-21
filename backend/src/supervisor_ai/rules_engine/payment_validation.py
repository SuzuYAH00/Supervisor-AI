from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from enum import StrEnum

from supervisor_ai.rules_engine.remuneration_eligibility import (
    RemunerationEligibilityResult,
    RemunerationEligibilityStatus,
)

PAYMENT_DEADLINE_DAYS = 35


class InvoicePaymentStatus(StrEnum):
    """Situação financeira normalizada necessária à validação."""

    PAID = "paid"
    UNPAID = "unpaid"


class PaymentValidationStatus(StrEnum):
    """Estados da validação financeira, sem materializar pagamento."""

    VALIDATED = "validated"
    PENDING_PAYMENT = "pending_payment"
    EXPIRED = "expired"
    NOT_ELIGIBLE = "not_eligible"
    PENDING_MANUAL_REVIEW = "pending_manual_review"
    NOT_EVALUABLE = "not_evaluable"


class PaymentValidationReason(StrEnum):
    """Motivos estáveis do resultado da validação financeira."""

    ELIGIBILITY_NOT_APPROVED = "eligibility_not_approved"
    ELIGIBILITY_PENDING_REVIEW = "eligibility_pending_review"
    EVENT_ALREADY_VALIDATED = "event_already_validated"
    INVOICE_NOT_LINKED_TO_EVENT = "invoice_not_linked_to_event"
    FIRST_NEW_VALUE_INVOICE_NOT_IDENTIFIED = (
        "first_new_value_invoice_not_identified"
    )
    MULTIPLE_FIRST_INVOICE_CANDIDATES = "multiple_first_invoice_candidates"
    INVOICE_AMOUNT_MISMATCH = "invoice_amount_mismatch"
    INVOICE_NOT_PAID = "invoice_not_paid"
    PAYMENT_WITHIN_DEADLINE = "payment_within_deadline"
    PAYMENT_AFTER_DEADLINE = "payment_after_deadline"
    MISSING_DUE_DATE = "missing_due_date"
    MISSING_PAYMENT_DATE = "missing_payment_date"
    INSUFFICIENT_FINANCIAL_DATA = "insufficient_financial_data"
    INCONSISTENT_FINANCIAL_INPUT = "inconsistent_financial_input"
    DUPLICATE_INVOICE_EVENT_LINK = "duplicate_invoice_event_link"


@dataclass(frozen=True, slots=True)
class PaymentValidationInput:
    """Snapshot financeiro mínimo recebido pela Fase E.

    ``evaluated_at`` torna determinística a avaliação de faturas ainda não
    pagas. Os identificadores de referência preservam auditoria sem carregar
    objetos de infraestrutura.
    """

    event_id: str
    eligibility_result: RemunerationEligibilityResult
    evaluated_at: datetime
    invoice_id: str | None
    invoice_due_date: date | None
    invoice_paid_at: datetime | None
    invoice_status: InvoicePaymentStatus | None
    invoice_recurring_amount: Decimal | None
    expected_recurring_amount: Decimal | None
    invoice_linked_to_event: bool | None
    is_first_new_value_invoice: bool | None
    first_invoice_candidate_count: int | None
    already_validated_event_ids: tuple[str, ...] = ()
    financial_reference_ids: tuple[str, ...] = ()
    has_link_conflict: bool = False
    has_duplicate_invoice_event_link: bool = False
    has_inconsistent_financial_input: bool = False


@dataclass(frozen=True, slots=True)
class PaymentValidationResult:
    """Resultado auditável sem criar crédito ou registro de pagamento."""

    status: PaymentValidationStatus
    reasons: tuple[PaymentValidationReason, ...]
    event_id: str
    invoice_id: str | None
    eligibility_conclusion_ids: tuple[str, ...]
    financial_reference_ids: tuple[str, ...]
    deadline_date: date | None = None
    validated_at: datetime | None = None


class PaymentValidationEvaluator:
    """Valida a evidência financeira sem consultar ou alterar estado externo."""

    def evaluate(self, data: PaymentValidationInput) -> PaymentValidationResult:
        eligibility_ids = tuple(
            sorted(
                (
                    *data.eligibility_result.commercial_conclusion_ids,
                    *data.eligibility_result.operational_conclusion_ids,
                )
            )
        )
        financial_ids = tuple(sorted(data.financial_reference_ids))

        if self._is_inconsistent(data):
            return self._result(
                data,
                PaymentValidationStatus.NOT_EVALUABLE,
                (PaymentValidationReason.INCONSISTENT_FINANCIAL_INPUT,),
                eligibility_ids,
                financial_ids,
            )

        eligibility_status = data.eligibility_result.status
        if eligibility_status is RemunerationEligibilityStatus.NOT_EVALUABLE:
            return self._result(
                data,
                PaymentValidationStatus.NOT_EVALUABLE,
                (PaymentValidationReason.ELIGIBILITY_NOT_APPROVED,),
                eligibility_ids,
                financial_ids,
            )
        if (
            eligibility_status
            is RemunerationEligibilityStatus.PENDING_MANUAL_REVIEW
        ):
            return self._result(
                data,
                PaymentValidationStatus.PENDING_MANUAL_REVIEW,
                (PaymentValidationReason.ELIGIBILITY_PENDING_REVIEW,),
                eligibility_ids,
                financial_ids,
            )
        if eligibility_status is RemunerationEligibilityStatus.NOT_ELIGIBLE:
            return self._result(
                data,
                PaymentValidationStatus.NOT_ELIGIBLE,
                (PaymentValidationReason.ELIGIBILITY_NOT_APPROVED,),
                eligibility_ids,
                financial_ids,
            )

        if data.event_id in data.already_validated_event_ids:
            return self._result(
                data,
                PaymentValidationStatus.VALIDATED,
                (PaymentValidationReason.EVENT_ALREADY_VALIDATED,),
                eligibility_ids,
                financial_ids,
            )

        review_reasons: list[PaymentValidationReason] = []
        if data.has_link_conflict:
            review_reasons.append(
                PaymentValidationReason.INVOICE_NOT_LINKED_TO_EVENT
            )
        if data.has_duplicate_invoice_event_link:
            review_reasons.append(
                PaymentValidationReason.DUPLICATE_INVOICE_EVENT_LINK
            )
        if (
            data.first_invoice_candidate_count is not None
            and data.first_invoice_candidate_count > 1
        ):
            review_reasons.append(
                PaymentValidationReason.MULTIPLE_FIRST_INVOICE_CANDIDATES
            )
        if review_reasons:
            return self._result(
                data,
                PaymentValidationStatus.PENDING_MANUAL_REVIEW,
                tuple(review_reasons),
                eligibility_ids,
                financial_ids,
            )

        missing_reason = self._missing_reason(data)
        if missing_reason is not None:
            return self._result(
                data,
                PaymentValidationStatus.NOT_EVALUABLE,
                (missing_reason,),
                eligibility_ids,
                financial_ids,
            )

        deadline = data.invoice_due_date + timedelta(days=PAYMENT_DEADLINE_DAYS)
        if not data.invoice_linked_to_event:
            return self._result(
                data,
                PaymentValidationStatus.NOT_ELIGIBLE,
                (PaymentValidationReason.INVOICE_NOT_LINKED_TO_EVENT,),
                eligibility_ids,
                financial_ids,
                deadline,
            )
        if not data.is_first_new_value_invoice:
            return self._result(
                data,
                PaymentValidationStatus.NOT_EVALUABLE,
                (
                    PaymentValidationReason.FIRST_NEW_VALUE_INVOICE_NOT_IDENTIFIED,
                ),
                eligibility_ids,
                financial_ids,
                deadline,
            )
        if data.invoice_recurring_amount != data.expected_recurring_amount:
            return self._result(
                data,
                PaymentValidationStatus.PENDING_MANUAL_REVIEW,
                (PaymentValidationReason.INVOICE_AMOUNT_MISMATCH,),
                eligibility_ids,
                financial_ids,
                deadline,
            )

        if data.invoice_status is InvoicePaymentStatus.UNPAID:
            if data.evaluated_at.date() > deadline:
                return self._result(
                    data,
                    PaymentValidationStatus.EXPIRED,
                    (
                        PaymentValidationReason.INVOICE_NOT_PAID,
                        PaymentValidationReason.PAYMENT_AFTER_DEADLINE,
                    ),
                    eligibility_ids,
                    financial_ids,
                    deadline,
                )
            return self._result(
                data,
                PaymentValidationStatus.PENDING_PAYMENT,
                (PaymentValidationReason.INVOICE_NOT_PAID,),
                eligibility_ids,
                financial_ids,
                deadline,
            )

        if data.invoice_paid_at.date() > deadline:
            return self._result(
                data,
                PaymentValidationStatus.EXPIRED,
                (PaymentValidationReason.PAYMENT_AFTER_DEADLINE,),
                eligibility_ids,
                financial_ids,
                deadline,
            )
        return self._result(
            data,
            PaymentValidationStatus.VALIDATED,
            (PaymentValidationReason.PAYMENT_WITHIN_DEADLINE,),
            eligibility_ids,
            financial_ids,
            deadline,
            data.invoice_paid_at,
        )

    @staticmethod
    def _result(
        data: PaymentValidationInput,
        status: PaymentValidationStatus,
        reasons: tuple[PaymentValidationReason, ...],
        eligibility_ids: tuple[str, ...],
        financial_ids: tuple[str, ...],
        deadline: date | None = None,
        validated_at: datetime | None = None,
    ) -> PaymentValidationResult:
        return PaymentValidationResult(
            status=status,
            reasons=reasons,
            event_id=data.event_id,
            invoice_id=data.invoice_id,
            eligibility_conclusion_ids=eligibility_ids,
            financial_reference_ids=financial_ids,
            deadline_date=deadline,
            validated_at=validated_at,
        )

    @staticmethod
    def _is_inconsistent(data: PaymentValidationInput) -> bool:
        return any(
            (
                data.has_inconsistent_financial_input,
                not data.event_id,
                not _is_aware(data.evaluated_at),
                data.invoice_due_date is not None
                and type(data.invoice_due_date) is not date,
                data.invoice_paid_at is not None
                and not _is_aware(data.invoice_paid_at),
                data.invoice_status is not None
                and not isinstance(data.invoice_status, InvoicePaymentStatus),
                data.invoice_recurring_amount is not None
                and (
                    not isinstance(data.invoice_recurring_amount, Decimal)
                    or not data.invoice_recurring_amount.is_finite()
                ),
                data.expected_recurring_amount is not None
                and (
                    not isinstance(data.expected_recurring_amount, Decimal)
                    or not data.expected_recurring_amount.is_finite()
                ),
                data.invoice_linked_to_event is not None
                and type(data.invoice_linked_to_event) is not bool,
                data.is_first_new_value_invoice is not None
                and type(data.is_first_new_value_invoice) is not bool,
                data.first_invoice_candidate_count is not None
                and (
                    type(data.first_invoice_candidate_count) is not int
                    or data.first_invoice_candidate_count < 0
                ),
                data.invoice_status is InvoicePaymentStatus.UNPAID
                and data.invoice_paid_at is not None,
            )
        )

    @staticmethod
    def _missing_reason(
        data: PaymentValidationInput,
    ) -> PaymentValidationReason | None:
        if data.invoice_due_date is None:
            return PaymentValidationReason.MISSING_DUE_DATE
        if (
            data.invoice_status is InvoicePaymentStatus.PAID
            and data.invoice_paid_at is None
        ):
            return PaymentValidationReason.MISSING_PAYMENT_DATE
        if data.first_invoice_candidate_count == 0:
            return PaymentValidationReason.FIRST_NEW_VALUE_INVOICE_NOT_IDENTIFIED
        required = (
            data.invoice_id,
            data.invoice_status,
            data.invoice_recurring_amount,
            data.expected_recurring_amount,
            data.invoice_linked_to_event,
            data.is_first_new_value_invoice,
            data.first_invoice_candidate_count,
        )
        if any(item is None for item in required):
            return PaymentValidationReason.INSUFFICIENT_FINANCIAL_DATA
        return None


def _is_aware(value: datetime) -> bool:
    return value.tzinfo is not None and value.utcoffset() is not None
