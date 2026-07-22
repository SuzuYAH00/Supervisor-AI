import json
from copy import deepcopy


def document() -> dict[str, object]:
    return {
        "event": {
            "id": "event-json-1",
            "external_reference": "external-json-1",
            "source": "json-test",
            "occurred_at": "2026-07-21T10:00:00-03:00",
            "received_at": "2026-07-21T13:01:00Z",
            "raw_payload": {
                "contract_id": "contract-1",
                "nested": {"items": [1, True, None]},
            },
        },
        "evaluation": {
            "evaluation_id": "00000000-0000-0000-0000-000000000001",
            "subject_id": "contract-1",
            "observed_at": "2026-07-21T13:00:00Z",
            "evidence": [],
        },
        "rules_engine_version": "rules-json-1",
    }


def json_text(value: dict[str, object] | None = None) -> str:
    return json.dumps(deepcopy(value or document()))


def evidence(
    evidence_id: str,
    name: str,
    value: object,
    *,
    observed_at: str = "2026-07-21T13:00:00Z",
) -> dict[str, object]:
    return {
        "id": evidence_id,
        "name": name,
        "value": value,
        "observed_at": observed_at,
    }


def complete_financial_snapshot() -> dict[str, object]:
    return {
        "payment": {
            "evaluated_at": "2026-07-21T13:00:00Z",
            "invoice_id": "invoice-1",
            "invoice_due_date": "2026-07-10",
            "invoice_paid_at": "2026-07-11T12:00:00Z",
            "invoice_status": "paid",
            "invoice_recurring_amount": "99.90",
            "expected_recurring_amount": "99.90",
            "invoice_linked_to_event": True,
            "is_first_new_value_invoice": True,
            "first_invoice_candidate_count": 1,
            "already_validated_event_ids": [],
            "financial_reference_ids": ["invoice-1", "payment-1"],
            "has_link_conflict": False,
            "has_duplicate_invoice_event_link": False,
            "has_inconsistent_financial_input": False,
        },
        "remuneration": {
            "payment_validation_reference": "payment-validation:event-json-1",
            "previous_recurring_amount": "89.90",
            "new_recurring_amount": "99.90",
            "full_new_plan_amount": "99.90",
            "additional_type": None,
            "renews_loyalty": True,
            "commercial_reference_ids": ["contract-change-1"],
            "calculation_reference_ids": ["calculation-input-1"],
            "has_commercial_classification_conflict": False,
            "has_inconsistent_input": False,
        },
        "posting": {
            "beneficiary_id": "employee-1",
            "posted_at": "2026-07-21T13:05:00Z",
            "posting_reference": "posting:event-json-1",
            "source_reference_ids": ["invoice-1", "ticket-1"],
            "remuneration_calculation_reference": "calculation:event-json-1",
            "has_ledger_reference_conflict": False,
            "has_inconsistent_input": False,
        },
    }


def complete_document() -> dict[str, object]:
    value = document()
    evaluation = value["evaluation"]
    assert isinstance(evaluation, dict)
    evaluation["evidence"] = [
        evidence("previous-speed", "previous_speed", 500),
        evidence("current-speed", "current_speed", 1000),
        evidence("previous-modality", "previous_plan_modality", "standard"),
        evidence("current-modality", "current_plan_modality", "standard"),
        evidence("previous-mesh", "previous_mesh_enabled", False),
        evidence("current-mesh", "current_mesh_enabled", False),
        evidence("previous-additionals", "previous_additionals", []),
        evidence("current-additionals", "current_additionals", []),
        evidence("previous-value", "previous_recurring_value", 89.90),
        evidence("current-value", "current_recurring_value", 99.90),
        evidence("ticket", "ticket_found", "ticket-1"),
        evidence("support", "ticket_opened_by_support", "employee-1"),
        evidence("author", "ticket_author_identified", "employee-1"),
        evidence("duplicate", "duplicate_author_not_detected", None),
        evidence("purpose", "ticket_linked_to_plan_change", "ticket-1"),
        evidence("administrative", "change_not_marked_administrative", False),
        evidence("corrective", "change_not_marked_corrective", False),
        evidence(
            "authorship",
            "conflicting_authorship_evidence_not_found",
            False,
        ),
    ]
    value["financial_snapshot"] = complete_financial_snapshot()
    return value
