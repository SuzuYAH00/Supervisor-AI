from dataclasses import dataclass

from supervisor_ai.application.use_cases import (
    CommercialEventPhase,
    PhaseResult,
    ProcessCommercialEventCommand,
)
from supervisor_ai.rules_engine import (
    CommercialClassificationName,
    CommercialEventType,
    ConclusionKind,
    ConclusionStatus,
    ContractualFactName,
    EvaluationConclusion,
    Justification,
    LedgerPostingInput,
    OperationalFactName,
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


class OperationalRulesPhaseHandler(RulesPhaseHandler):
    def execute(
        self,
        command: ProcessCommercialEventCommand,
        previous_results: tuple[PhaseResult, ...],
    ) -> PhaseResult:
        prepared = _operational_conclusions(command)
        seed = PhaseResult(
            phase=CommercialEventPhase.OPERATIONAL_CONTEXT,
            status="prepared",
            output=ConclusionsOutput(prepared),
        )
        evaluated = super().execute(command, (*previous_results, seed))
        output = _output((evaluated,), ConclusionsOutput)
        conclusions = (*prepared, *output.conclusions)
        return PhaseResult(
            phase=CommercialEventPhase.OPERATIONAL_CONTEXT,
            status=evaluated.status,
            output=ConclusionsOutput(conclusions),
            audit_references=tuple(item.conclusion_id for item in conclusions),
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
        snapshot = command.financial_snapshot
        if snapshot is None:
            payment_input = PaymentValidationInput(
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
        else:
            facts = snapshot.payment
            payment_input = PaymentValidationInput(
                event_id=command.event_id,
                eligibility_result=eligibility,
                evaluated_at=facts.evaluated_at,
                invoice_id=facts.invoice_id,
                invoice_due_date=facts.invoice_due_date,
                invoice_paid_at=facts.invoice_paid_at,
                invoice_status=facts.invoice_status,
                invoice_recurring_amount=facts.invoice_recurring_amount,
                expected_recurring_amount=facts.expected_recurring_amount,
                invoice_linked_to_event=facts.invoice_linked_to_event,
                is_first_new_value_invoice=facts.is_first_new_value_invoice,
                first_invoice_candidate_count=facts.first_invoice_candidate_count,
                already_validated_event_ids=facts.already_validated_event_ids,
                financial_reference_ids=facts.financial_reference_ids,
                has_link_conflict=facts.has_link_conflict,
                has_duplicate_invoice_event_link=(
                    facts.has_duplicate_invoice_event_link
                ),
                has_inconsistent_financial_input=(
                    facts.has_inconsistent_financial_input
                ),
            )
        result = self._evaluator.evaluate(
            payment_input
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
        commercial_event_type, classification_conflict = _commercial_event_type(
            _conclusions(previous_results)
        )
        snapshot = command.financial_snapshot
        if snapshot is None:
            amount_input = RemunerationAmountInput(
                event_id=command.event_id,
                payment_validation_result=payment,
                payment_validation_reference=(
                    f"rules:{command.event_id}:payment-validation"
                ),
                commercial_event_type=commercial_event_type,
                has_commercial_classification_conflict=classification_conflict,
            )
        else:
            facts = snapshot.remuneration
            amount_input = RemunerationAmountInput(
                event_id=command.event_id,
                payment_validation_result=payment,
                payment_validation_reference=facts.payment_validation_reference,
                commercial_event_type=commercial_event_type,
                previous_recurring_amount=facts.previous_recurring_amount,
                new_recurring_amount=facts.new_recurring_amount,
                full_new_plan_amount=facts.full_new_plan_amount,
                additional_type=facts.additional_type,
                renews_loyalty=facts.renews_loyalty,
                commercial_reference_ids=facts.commercial_reference_ids,
                calculation_reference_ids=facts.calculation_reference_ids,
                has_commercial_classification_conflict=(
                    facts.has_commercial_classification_conflict
                    or classification_conflict
                ),
                has_inconsistent_input=facts.has_inconsistent_input,
            )
        result = self._evaluator.evaluate(
            amount_input
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
        snapshot = command.financial_snapshot
        if snapshot is None:
            ledger_input = LedgerPostingInput(
                event_id=command.event_id,
                beneficiary_id=None,
                remuneration_amount_result=amount,
                posted_at=None,
                posting_reference=None,
                source_reference_ids=(),
                remuneration_calculation_reference=None,
            )
        else:
            facts = snapshot.posting
            ledger_input = LedgerPostingInput(
                event_id=command.event_id,
                beneficiary_id=facts.beneficiary_id,
                remuneration_amount_result=amount,
                posted_at=facts.posted_at,
                posting_reference=facts.posting_reference,
                source_reference_ids=facts.source_reference_ids,
                remuneration_calculation_reference=(
                    facts.remuneration_calculation_reference
                ),
                invoice_id=snapshot.payment.invoice_id,
                has_ledger_reference_conflict=(
                    facts.has_ledger_reference_conflict
                ),
                has_inconsistent_input=facts.has_inconsistent_input,
            )
        result = self._evaluator.evaluate(
            ledger_input
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


def _operational_conclusions(
    command: ProcessCommercialEventCommand,
) -> tuple[EvaluationConclusion, ...]:
    conclusions: list[EvaluationConclusion] = []
    for evidence in command.evaluation_context.evidence:
        try:
            fact_name = OperationalFactName(evidence.name)
        except ValueError:
            continue
        name: str = fact_name
        status = ConclusionStatus.TRUE
        if name.endswith("_not_evaluable"):
            status = ConclusionStatus.NOT_EVALUABLE
        elif name.endswith("_inconsistent"):
            status = ConclusionStatus.INCONSISTENT
        conclusions.append(
            EvaluationConclusion(
                conclusion_id=f"input.{evidence.evidence_id}.{name}",
                name=name,
                kind=ConclusionKind.DERIVED_FACT,
                status=status,
                justification=Justification(
                    rule_id="input.operational_evidence",
                    summary="Operational input prepared for rules evaluation.",
                    evidence_ids=(evidence.evidence_id,),
                ),
                value=evidence.value,
            )
        )
    return tuple(conclusions)


def _commercial_event_type(
    conclusions: tuple[EvaluationConclusion, ...],
) -> tuple[CommercialEventType | None, bool]:
    """Traduz conclusões da classificação sem reavaliar evidências comerciais."""

    relevant_names = {
        *CommercialClassificationName,
        ContractualFactName.MESH_INCLUDED,
    }
    relevant = tuple(item for item in conclusions if item.name in relevant_names)
    if any(item.status is ConclusionStatus.INCONSISTENT for item in relevant):
        return None, True

    true_names = {
        item.name for item in relevant if item.status is ConclusionStatus.TRUE
    }
    revenue_names = true_names & {
        CommercialClassificationName.COMMERCIAL_UPGRADE,
        CommercialClassificationName.COMMERCIAL_DOWNGRADE,
        CommercialClassificationName.RECURRING_REVENUE_UNCHANGED,
    }
    if len(revenue_names) != 1:
        return (None, len(revenue_names) > 1)
    revenue = next(iter(revenue_names))
    if revenue is CommercialClassificationName.COMMERCIAL_DOWNGRADE:
        return CommercialEventType.DOWNGRADE, False
    if revenue is CommercialClassificationName.RECURRING_REVENUE_UNCHANGED:
        return CommercialEventType.UNSUPPORTED_COMMERCIAL_EVENT, False
    if (
        CommercialClassificationName.COMMON_ADDITIONAL_SALE in true_names
        and CommercialClassificationName.ADDITIONAL_ONLY_OPERATION in true_names
    ):
        return CommercialEventType.NON_LOYALTY_ADDITIONAL, False
    if ContractualFactName.MESH_INCLUDED in true_names:
        return CommercialEventType.MESH_UPGRADE, False
    if CommercialClassificationName.PLAN_CHANGED in true_names:
        return CommercialEventType.PLAN_UPGRADE, False
    return None, False
