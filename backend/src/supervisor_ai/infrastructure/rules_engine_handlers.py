from dataclasses import dataclass

from supervisor_ai.application.use_cases import (
    CommercialEventPhase,
    PhaseResult,
    ProcessCommercialEventCommand,
)
from supervisor_ai.rules_engine import (
    CommercialEventType,
    EvaluationConclusion,
    LedgerPostingInput,
    PaymentValidationEvaluator,
    PaymentValidationInput,
    PaymentValidationResult,
    RemunerationAmountEvaluator,
    RemunerationAmountInput,
    RemunerationAmountResult,
    RemunerationEligibilityEvaluator,
    RemunerationEligibilityResult,
    RemunerationLedgerPostingEvaluator,
    Rule,
)


@dataclass(frozen=True, slots=True)
class ConclusionsOutput:
    conclusions: tuple[EvaluationConclusion, ...]


class RulesPhaseHandler:
    def __init__(self, phase: CommercialEventPhase, rules: tuple[Rule, ...]) -> None:
        self._phase = phase
        self._rules = rules

    def execute(
        self,
        command: ProcessCommercialEventCommand,
        previous_results: tuple[PhaseResult, ...],
    ) -> PhaseResult:
        conclusions = list(_conclusions(previous_results))
        initial_count = len(conclusions)
        for rule in self._rules:
            conclusions.extend(
                rule.evaluate(command.evaluation_context, tuple(conclusions))
            )
        produced = tuple(conclusions[initial_count:])
        return PhaseResult(
            phase=self._phase,
            status="completed",
            output=ConclusionsOutput(produced),
            audit_references=tuple(item.conclusion_id for item in produced),
        )


class RemunerationEligibilityPhaseHandler:
    def __init__(self, evaluator: RemunerationEligibilityEvaluator) -> None:
        self._evaluator = evaluator

    def execute(
        self,
        command: ProcessCommercialEventCommand,
        previous_results: tuple[PhaseResult, ...],
    ) -> PhaseResult:
        del command
        result = self._evaluator.evaluate(_conclusions(previous_results))
        return PhaseResult(
            phase=CommercialEventPhase.REMUNERATION_ELIGIBILITY,
            status=result.status.value,
            output=result,
            audit_references=(
                *result.commercial_conclusion_ids,
                *result.operational_conclusion_ids,
            ),
        )


class PaymentValidationPhaseHandler:
    """Executa a fase financeira sem presumir evidências ainda não fornecidas."""

    def __init__(self, evaluator: PaymentValidationEvaluator) -> None:
        self._evaluator = evaluator

    def execute(
        self,
        command: ProcessCommercialEventCommand,
        previous_results: tuple[PhaseResult, ...],
    ) -> PhaseResult:
        eligibility = _output(previous_results, RemunerationEligibilityResult)
        result = self._evaluator.evaluate(
            PaymentValidationInput(
                event_id=command.event_id,
                eligibility_result=eligibility,
                evaluated_at=command.evaluation_context.observed_at,
                invoice_id=None,
                invoice_due_date=None,
                invoice_paid_at=None,
                invoice_status=None,
                invoice_recurring_amount=None,
                expected_recurring_amount=None,
                invoice_linked_to_event=None,
                is_first_new_value_invoice=None,
                first_invoice_candidate_count=None,
            )
        )
        return PhaseResult(
            phase=CommercialEventPhase.PAYMENT_VALIDATION,
            status=result.status.value,
            output=result,
            audit_references=result.financial_reference_ids,
        )


class RemunerationAmountPhaseHandler:
    def __init__(self, evaluator: RemunerationAmountEvaluator) -> None:
        self._evaluator = evaluator

    def execute(
        self,
        command: ProcessCommercialEventCommand,
        previous_results: tuple[PhaseResult, ...],
    ) -> PhaseResult:
        payment = _output(previous_results, PaymentValidationResult)
        reference = f"rules:{command.event_id}:payment-validation"
        result = self._evaluator.evaluate(
            RemunerationAmountInput(
                event_id=command.event_id,
                payment_validation_result=payment,
                payment_validation_reference=reference,
                commercial_event_type=(
                    CommercialEventType.UNSUPPORTED_COMMERCIAL_EVENT
                ),
            )
        )
        return PhaseResult(
            phase=CommercialEventPhase.REMUNERATION_AMOUNT,
            status=result.status.value,
            output=result,
            audit_references=result.calculation_reference_ids,
        )


class LedgerPostingPhaseHandler:
    def __init__(self, evaluator: RemunerationLedgerPostingEvaluator) -> None:
        self._evaluator = evaluator

    def execute(
        self,
        command: ProcessCommercialEventCommand,
        previous_results: tuple[PhaseResult, ...],
    ) -> PhaseResult:
        amount = _output(previous_results, RemunerationAmountResult)
        result = self._evaluator.evaluate(
            LedgerPostingInput(
                event_id=command.event_id,
                beneficiary_id=None,
                remuneration_amount_result=amount,
                posted_at=None,
                posting_reference=None,
                source_reference_ids=(),
                remuneration_calculation_reference=None,
            )
        )
        return PhaseResult(
            phase=CommercialEventPhase.LEDGER_POSTING,
            status=result.status.value,
            output=result,
            ledger_entry=result.entry,
            audit_references=result.source_reference_ids,
        )


def _conclusions(
    previous_results: tuple[PhaseResult, ...],
) -> tuple[EvaluationConclusion, ...]:
    return tuple(
        conclusion
        for phase in previous_results
        if isinstance(phase.output, ConclusionsOutput)
        for conclusion in phase.output.conclusions
    )


def _output[T](previous_results: tuple[PhaseResult, ...], expected: type[T]) -> T:
    for phase in reversed(previous_results):
        if isinstance(phase.output, expected):
            return phase.output
    raise RuntimeError(f"missing phase output for {expected.__name__}")
