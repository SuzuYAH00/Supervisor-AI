from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

import supervisor_ai.rules_engine as rules_engine
from supervisor_ai.rules_engine import (
    CandidateDomainEvent,
    ConclusionKind,
    ConclusionStatus,
    EvaluationConclusion,
    EvaluationContext,
    EvaluationResult,
    Evidence,
    Justification,
    Rule,
    RulePhase,
)


class StructuralRule:
    @property
    def rule_id(self) -> str:
        return "technical.example"

    @property
    def phase(self) -> RulePhase:
        return RulePhase.CONTRACTUAL_FACTS

    def evaluate(
        self,
        context: EvaluationContext,
        available_conclusions: tuple[EvaluationConclusion, ...],
    ) -> tuple[EvaluationConclusion, ...]:
        del context, available_conclusions
        return ()


def make_evidence() -> Evidence:
    return Evidence(
        evidence_id="contract.values",
        name="recurring_values",
        value=(Decimal("89.90"), Decimal("99.90")),
        observed_at=datetime(2026, 7, 20, tzinfo=UTC),
        source_reference="contract:123",
    )


def test_evaluation_context_is_an_immutable_snapshot() -> None:
    evidence = make_evidence()
    context = EvaluationContext(
        evaluation_id=uuid4(),
        subject_id="commercial-event:456",
        observed_at=datetime(2026, 7, 20, tzinfo=UTC),
        evidence=(evidence,),
    )

    assert context.evidence == (evidence,)
    with pytest.raises(FrozenInstanceError):
        context.subject_id = "another-event"  # type: ignore[misc]


def test_conclusion_separates_kind_status_and_justification() -> None:
    justification = Justification(
        rule_id="technical.example",
        summary="Conclusion derived from the available evidence.",
        evidence_ids=("contract.values",),
    )
    conclusion = EvaluationConclusion(
        conclusion_id="conclusion:1",
        name="example_conclusion",
        kind=ConclusionKind.DERIVED_FACT,
        status=ConclusionStatus.TRUE,
        justification=justification,
    )

    assert conclusion.kind is ConclusionKind.DERIVED_FACT
    assert conclusion.status is ConclusionStatus.TRUE
    assert conclusion.justification is justification


def test_all_architectural_conclusion_statuses_are_available() -> None:
    assert set(ConclusionStatus) == {
        ConclusionStatus.TRUE,
        ConclusionStatus.FALSE,
        ConclusionStatus.INDETERMINATE,
        ConclusionStatus.NOT_EVALUABLE,
        ConclusionStatus.INCONSISTENT,
        ConclusionStatus.PENDING_HUMAN_REVIEW,
    }


def test_evaluation_result_keeps_auditable_references() -> None:
    evaluation_id = uuid4()
    evidence = make_evidence()
    justification = Justification(
        rule_id="technical.example",
        summary="Review is required.",
        evidence_ids=(evidence.evidence_id,),
    )
    conclusion = EvaluationConclusion(
        conclusion_id="conclusion:review",
        name="manual_review_required",
        kind=ConclusionKind.DOMAIN_DECISION,
        status=ConclusionStatus.PENDING_HUMAN_REVIEW,
        justification=justification,
    )
    candidate_event = CandidateDomainEvent(
        name="ReviewRequested",
        subject_id="commercial-event:456",
        supporting_conclusion_ids=(conclusion.conclusion_id,),
        justification=justification,
    )

    result = EvaluationResult(
        evaluation_id=evaluation_id,
        conclusions=(conclusion,),
        evidence=(evidence,),
        missing_information=("confirmed_author",),
        manual_review_reasons=("conflicting_candidates",),
        candidate_domain_events=(candidate_event,),
    )

    assert result.evaluation_id is evaluation_id
    assert result.conclusions == (conclusion,)
    assert result.evidence == (evidence,)
    assert result.candidate_domain_events == (candidate_event,)


def test_rule_supports_structural_typing_without_inheritance() -> None:
    rule = StructuralRule()

    assert isinstance(rule, Rule)
    assert rule.evaluate(
        EvaluationContext(
            evaluation_id=uuid4(),
            subject_id="commercial-event:456",
            observed_at=datetime(2026, 7, 20, tzinfo=UTC),
            evidence=(),
        ),
        (),
    ) == ()


def test_public_api_exports_only_the_contract_surface() -> None:
    assert set(rules_engine.__all__) == {
        "CandidateDomainEvent",
        "CommercialClassificationName",
        "CommercialEventType",
        "CommercialAuthorRule",
        "CommonAdditionalClassificationRule",
        "CommonAdditionalsComparisonRule",
        "ConclusionKind",
        "ConclusionStatus",
        "ContractualEvidenceName",
        "ContractualFactName",
        "Currency",
        "EvaluationConclusion",
        "EvaluationContext",
        "EvaluationResult",
        "Evidence",
        "EvidenceValue",
        "Justification",
        "InvoicePaymentStatus",
        "MeshComparisonRule",
        "NonLoyaltyAdditionalType",
        "DuplicateAuthorRule",
        "ManualReviewRule",
        "OperationalDecisionName",
        "OperationalFactName",
        "OperationalContextEligibilityRule",
        "OperationScopeClassificationRule",
        "PlanModalityComparisonRule",
        "PlanChangeClassificationRule",
        "PaymentValidationEvaluator",
        "PaymentValidationInput",
        "PaymentValidationReason",
        "PaymentValidationResult",
        "PaymentValidationStatus",
        "RecurringRevenueClassificationRule",
        "RecurringValueComparisonRule",
        "RemunerationAmountEvaluator",
        "RemunerationAmountInput",
        "RemunerationAmountReason",
        "RemunerationAmountResult",
        "RemunerationAmountStatus",
        "RemunerationCalculationMethod",
        "RemunerationEligibilityEvaluator",
        "RemunerationEligibilityReason",
        "RemunerationEligibilityResult",
        "RemunerationEligibilityStatus",
        "Rule",
        "RulePhase",
        "SpeedComparisonRule",
        "TicketPresenceRule",
        "TicketSupportRule",
    }
