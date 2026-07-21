from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from supervisor_ai.rules_engine.payment_validation import (
    PaymentValidationResult,
    PaymentValidationStatus,
)


class CommercialEventType(StrEnum):
    """Tipos comerciais com política conhecida pela Fase F1."""

    PLAN_UPGRADE = "plan_upgrade"
    MESH_UPGRADE = "mesh_upgrade"
    NON_LOYALTY_ADDITIONAL = "non_loyalty_additional"
    DOWNGRADE = "downgrade"
    UNSUPPORTED_COMMERCIAL_EVENT = "unsupported_commercial_event"


class NonLoyaltyAdditionalType(StrEnum):
    """Adicionais comuns identificáveis sem definir preços nesta fase."""

    WATCH_TV = "watch_tv"
    PUBLIC_IP = "public_ip"
    CAMERA = "camera"
    OTHER = "other"


class RemunerationAmountStatus(StrEnum):
    """Estados do cálculo anterior à criação de qualquer lançamento."""

    CALCULATED = "calculated"
    NOT_APPLICABLE = "not_applicable"
    PENDING_MANUAL_REVIEW = "pending_manual_review"
    NOT_EVALUABLE = "not_evaluable"


class RemunerationAmountReason(StrEnum):
    """Motivos estáveis e auditáveis do cálculo."""

    PAYMENT_VALIDATED = "payment_validated"
    PAYMENT_NOT_VALIDATED = "payment_not_validated"
    PAYMENT_PENDING_MANUAL_REVIEW = "payment_pending_manual_review"
    FULL_NEW_PLAN_AMOUNT_USED = "full_new_plan_amount_used"
    RECURRING_DIFFERENCE_USED = "recurring_difference_used"
    MISSING_PREVIOUS_AMOUNT = "missing_previous_amount"
    MISSING_NEW_AMOUNT = "missing_new_amount"
    MISSING_FULL_PLAN_AMOUNT = "missing_full_plan_amount"
    NON_POSITIVE_REMUNERATION = "non_positive_remuneration"
    UNSUPPORTED_COMMERCIAL_EVENT = "unsupported_commercial_event"
    INCONSISTENT_INPUT = "inconsistent_input"
    INSUFFICIENT_DATA = "insufficient_data"
    COMMERCIAL_CLASSIFICATION_CONFLICT = "commercial_classification_conflict"


class RemunerationCalculationMethod(StrEnum):
    """Bases de cálculo permitidas pelas regras conhecidas."""

    FULL_NEW_PLAN_AMOUNT = "full_new_plan_amount"
    RECURRING_AMOUNT_DIFFERENCE = "recurring_amount_difference"
    NOT_CALCULATED = "not_calculated"


class Currency(StrEnum):
    """Moeda explícita do valor calculado."""

    BRL = "BRL"


@dataclass(frozen=True, slots=True)
class RemunerationAmountInput:
    """Dados comerciais mínimos para calcular um evento validado."""

    event_id: str
    payment_validation_result: PaymentValidationResult
    payment_validation_reference: str
    commercial_event_type: CommercialEventType
    previous_recurring_amount: Decimal | None = None
    new_recurring_amount: Decimal | None = None
    full_new_plan_amount: Decimal | None = None
    additional_type: NonLoyaltyAdditionalType | None = None
    renews_loyalty: bool | None = None
    commercial_reference_ids: tuple[str, ...] = ()
    calculation_reference_ids: tuple[str, ...] = ()
    has_commercial_classification_conflict: bool = False
    has_inconsistent_input: bool = False


@dataclass(frozen=True, slots=True)
class RemunerationAmountResult:
    """Valor calculado sem representar crédito, ledger ou pagamento bancário."""

    status: RemunerationAmountStatus
    reasons: tuple[RemunerationAmountReason, ...]
    event_id: str
    remuneration_amount: Decimal | None
    calculation_method: RemunerationCalculationMethod
    currency: Currency
    payment_validation_reference: str
    commercial_reference_ids: tuple[str, ...]
    calculation_reference_ids: tuple[str, ...]


class RemunerationAmountEvaluator:
    """Calcula a remuneração sem reexecutar classificação ou pagamento."""

    def evaluate(self, data: RemunerationAmountInput) -> RemunerationAmountResult:
        if self._is_inconsistent(data):
            return self._result(
                data,
                RemunerationAmountStatus.NOT_EVALUABLE,
                (RemunerationAmountReason.INCONSISTENT_INPUT,),
            )

        payment_status = data.payment_validation_result.status
        if payment_status is PaymentValidationStatus.NOT_EVALUABLE:
            return self._result(
                data,
                RemunerationAmountStatus.NOT_EVALUABLE,
                (RemunerationAmountReason.PAYMENT_NOT_VALIDATED,),
            )
        if payment_status is PaymentValidationStatus.PENDING_MANUAL_REVIEW:
            return self._result(
                data,
                RemunerationAmountStatus.PENDING_MANUAL_REVIEW,
                (RemunerationAmountReason.PAYMENT_PENDING_MANUAL_REVIEW,),
            )
        if payment_status is not PaymentValidationStatus.VALIDATED:
            return self._result(
                data,
                RemunerationAmountStatus.NOT_APPLICABLE,
                (RemunerationAmountReason.PAYMENT_NOT_VALIDATED,),
            )

        if data.has_commercial_classification_conflict:
            return self._result(
                data,
                RemunerationAmountStatus.PENDING_MANUAL_REVIEW,
                (
                    RemunerationAmountReason.PAYMENT_VALIDATED,
                    RemunerationAmountReason.COMMERCIAL_CLASSIFICATION_CONFLICT,
                ),
            )

        if (
            data.commercial_event_type
            in {
                CommercialEventType.DOWNGRADE,
                CommercialEventType.UNSUPPORTED_COMMERCIAL_EVENT,
            }
        ):
            return self._result(
                data,
                RemunerationAmountStatus.NOT_APPLICABLE,
                (
                    RemunerationAmountReason.PAYMENT_VALIDATED,
                    RemunerationAmountReason.UNSUPPORTED_COMMERCIAL_EVENT,
                ),
            )

        classification_error = self._classification_error(data)
        if classification_error is not None:
            return self._result(
                data,
                classification_error[0],
                (
                    RemunerationAmountReason.PAYMENT_VALIDATED,
                    classification_error[1],
                ),
            )

        if data.commercial_event_type in {
            CommercialEventType.PLAN_UPGRADE,
            CommercialEventType.MESH_UPGRADE,
        }:
            if data.full_new_plan_amount is None:
                return self._result(
                    data,
                    RemunerationAmountStatus.NOT_EVALUABLE,
                    (
                        RemunerationAmountReason.PAYMENT_VALIDATED,
                        RemunerationAmountReason.MISSING_FULL_PLAN_AMOUNT,
                    ),
                )
            amount = data.full_new_plan_amount
            method = RemunerationCalculationMethod.FULL_NEW_PLAN_AMOUNT
            basis_reason = RemunerationAmountReason.FULL_NEW_PLAN_AMOUNT_USED
        else:
            missing_reason = self._missing_additional_amount(data)
            if missing_reason is not None:
                return self._result(
                    data,
                    RemunerationAmountStatus.NOT_EVALUABLE,
                    (
                        RemunerationAmountReason.PAYMENT_VALIDATED,
                        missing_reason,
                    ),
                )
            amount = data.new_recurring_amount - data.previous_recurring_amount
            method = RemunerationCalculationMethod.RECURRING_AMOUNT_DIFFERENCE
            basis_reason = RemunerationAmountReason.RECURRING_DIFFERENCE_USED

        if amount <= Decimal("0"):
            return self._result(
                data,
                RemunerationAmountStatus.NOT_APPLICABLE,
                (
                    RemunerationAmountReason.PAYMENT_VALIDATED,
                    RemunerationAmountReason.NON_POSITIVE_REMUNERATION,
                ),
            )
        return self._result(
            data,
            RemunerationAmountStatus.CALCULATED,
            (RemunerationAmountReason.PAYMENT_VALIDATED, basis_reason),
            amount=amount,
            method=method,
        )

    @staticmethod
    def _result(
        data: RemunerationAmountInput,
        status: RemunerationAmountStatus,
        reasons: tuple[RemunerationAmountReason, ...],
        *,
        amount: Decimal | None = None,
        method: RemunerationCalculationMethod = (
            RemunerationCalculationMethod.NOT_CALCULATED
        ),
    ) -> RemunerationAmountResult:
        return RemunerationAmountResult(
            status=status,
            reasons=reasons,
            event_id=data.event_id,
            remuneration_amount=amount,
            calculation_method=method,
            currency=Currency.BRL,
            payment_validation_reference=data.payment_validation_reference,
            commercial_reference_ids=tuple(sorted(data.commercial_reference_ids)),
            calculation_reference_ids=tuple(
                sorted(data.calculation_reference_ids)
            ),
        )

    @staticmethod
    def _classification_error(
        data: RemunerationAmountInput,
    ) -> tuple[RemunerationAmountStatus, RemunerationAmountReason] | None:
        if data.renews_loyalty is None:
            return (
                RemunerationAmountStatus.NOT_EVALUABLE,
                RemunerationAmountReason.INSUFFICIENT_DATA,
            )
        is_plan_sale = data.commercial_event_type in {
            CommercialEventType.PLAN_UPGRADE,
            CommercialEventType.MESH_UPGRADE,
        }
        if is_plan_sale != data.renews_loyalty:
            return (
                RemunerationAmountStatus.PENDING_MANUAL_REVIEW,
                RemunerationAmountReason.COMMERCIAL_CLASSIFICATION_CONFLICT,
            )
        if (
            data.commercial_event_type is CommercialEventType.NON_LOYALTY_ADDITIONAL
            and data.additional_type is None
        ):
            return (
                RemunerationAmountStatus.NOT_EVALUABLE,
                RemunerationAmountReason.INSUFFICIENT_DATA,
            )
        return None

    @staticmethod
    def _missing_additional_amount(
        data: RemunerationAmountInput,
    ) -> RemunerationAmountReason | None:
        if data.previous_recurring_amount is None:
            return RemunerationAmountReason.MISSING_PREVIOUS_AMOUNT
        if data.new_recurring_amount is None:
            return RemunerationAmountReason.MISSING_NEW_AMOUNT
        return None

    @staticmethod
    def _is_inconsistent(data: RemunerationAmountInput) -> bool:
        money = (
            data.previous_recurring_amount,
            data.new_recurring_amount,
            data.full_new_plan_amount,
        )
        return any(
            (
                data.has_inconsistent_input,
                not data.event_id,
                data.payment_validation_result.event_id != data.event_id,
                not data.payment_validation_reference,
                not isinstance(data.commercial_event_type, CommercialEventType),
                data.additional_type is not None
                and not isinstance(data.additional_type, NonLoyaltyAdditionalType),
                data.renews_loyalty is not None
                and type(data.renews_loyalty) is not bool,
                any(
                    value is not None
                    and (
                        not isinstance(value, Decimal)
                        or not value.is_finite()
                        or value < Decimal("0")
                    )
                    for value in money
                ),
            )
        )
