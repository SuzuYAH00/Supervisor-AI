from dataclasses import replace
from datetime import UTC, datetime

from supervisor_ai.application.use_cases import ProcessCommercialEventCommand
from supervisor_ai.bootstrap import build_rules_engine
from supervisor_ai.infrastructure.importing.mapper import JsonImportDocumentMapper
from supervisor_ai.infrastructure.importing.parser import parse_json_text
from supervisor_ai.infrastructure.importing.schema import JsonImportDocumentValidator
from supervisor_ai.infrastructure.rules_engine_handlers import ConclusionsOutput
from supervisor_ai.rules_engine import (
    CommercialClassificationName,
    ContractualEvidenceName,
    Evidence,
    LedgerPostingStatus,
    OperationalDecisionName,
    PaymentValidationStatus,
    RemunerationEligibilityStatus,
)
from tests.importing.factories import complete_document, json_text


def command() -> ProcessCommercialEventCommand:
    transactional = JsonImportDocumentMapper().map(
        JsonImportDocumentValidator().validate(
            parse_json_text(json_text(complete_document()))
        )
    )
    return ProcessCommercialEventCommand(
        event_id=transactional.event.id,
        evaluation_context=transactional.evaluation_context,
        financial_snapshot=transactional.financial_snapshot,
    )


def test_complete_snapshot_reaches_real_ledger_posting() -> None:
    value = complete_document()
    serialized = json_text(value)
    assert "commercial_event_type" not in serialized
    evaluation = value["evaluation"]
    assert isinstance(evaluation, dict)
    evidence_documents = evaluation["evidence"]
    assert isinstance(evidence_documents, list)
    evidence_names = {
        item["name"] for item in evidence_documents if isinstance(item, dict)
    }
    assert evidence_names.isdisjoint(
        decision.value for decision in OperationalDecisionName
    )

    result = build_rules_engine().execute(command())
    commercial = result.phase_results[1].output
    operational = result.phase_results[2].output
    assert isinstance(commercial, ConclusionsOutput)
    assert isinstance(operational, ConclusionsOutput)
    assert CommercialClassificationName.COMMERCIAL_UPGRADE in {
        item.name for item in commercial.conclusions
    }
    assert {
        OperationalDecisionName.PLAN_CHANGE_TICKET,
        OperationalDecisionName.NON_ADMINISTRATIVE_CHANGE,
        OperationalDecisionName.NON_CORRECTIVE_CHANGE,
        OperationalDecisionName.NO_AUTHORSHIP_CONFLICT,
    } <= {item.name for item in operational.conclusions}
    assert result.phase_results[3].status == (
        RemunerationEligibilityStatus.POTENTIALLY_ELIGIBLE
    )
    assert result.phase_results[4].status == PaymentValidationStatus.VALIDATED
    assert result.final_status == LedgerPostingStatus.POSTED
    assert result.ledger_entry is not None
    assert result.ledger_entry.entry_id == (
        "ledger.remuneration.credit:event-json-1"
    )
    assert result.ledger_entry.beneficiary_id == "employee-1"
    assert result.ledger_entry.posted_at == datetime(
        2026, 7, 21, 13, 5, tzinfo=UTC
    )
    assert result.ledger_entry.posting_reference == "posting:event-json-1"
    assert result.ledger_entry.invoice_id == "invoice-1"
    assert "payment-1" in result.phase_results[4].audit_references


def test_missing_snapshot_keeps_safe_not_evaluable_behavior() -> None:
    value = command()
    without_snapshot = replace(value, financial_snapshot=None)
    result = build_rules_engine().execute(without_snapshot)
    assert result.final_status == LedgerPostingStatus.NOT_EVALUABLE
    assert result.ledger_entry is None


def test_partial_snapshot_does_not_invent_financial_facts() -> None:
    value = command()
    assert value.financial_snapshot is not None
    partial_payment = replace(
        value.financial_snapshot.payment,
        invoice_due_date=None,
        invoice_paid_at=None,
    )
    partial = replace(
        value,
        financial_snapshot=replace(
            value.financial_snapshot, payment=partial_payment
        ),
    )
    result = build_rules_engine().execute(partial)
    assert result.phase_results[4].status == PaymentValidationStatus.NOT_EVALUABLE
    assert result.ledger_entry is None


def test_same_snapshot_produces_identical_ledger_without_clock_or_uuid() -> None:
    processor = build_rules_engine()
    first = processor.execute(command())
    second = processor.execute(command())
    assert first.ledger_entry == second.ledger_entry
    assert first == second


def test_missing_commercial_classification_cannot_produce_credit() -> None:
    value = command()
    evidence = tuple(
        item
        for item in value.evaluation_context.evidence
        if not isinstance(item.name, ContractualEvidenceName)
    )
    result = build_rules_engine().execute(
        replace(
            value,
            evaluation_context=replace(value.evaluation_context, evidence=evidence),
        )
    )
    assert result.ledger_entry is None
    assert result.final_status == LedgerPostingStatus.NOT_EVALUABLE


def test_transport_decision_is_ignored_when_operational_fact_is_missing() -> None:
    value = command()
    evidence = tuple(
        item
        for item in value.evaluation_context.evidence
        if item.name != "ticket_linked_to_plan_change"
    )
    injected = Evidence(
        evidence_id="transport-decision",
        name=OperationalDecisionName.PLAN_CHANGE_TICKET,
        value=None,
        observed_at=value.evaluation_context.observed_at,
    )
    result = build_rules_engine().execute(
        replace(
            value,
            evaluation_context=replace(
                value.evaluation_context,
                evidence=(*evidence, injected),
            ),
        )
    )
    assert result.phase_results[3].status == RemunerationEligibilityStatus.NOT_EVALUABLE
    assert result.ledger_entry is None
