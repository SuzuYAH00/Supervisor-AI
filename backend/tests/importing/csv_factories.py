import csv
import io
import json

from supervisor_ai.infrastructure.importing import CSV_COLUMNS


def csv_row(index: int = 1) -> dict[str, str]:
    event_id = f"event-csv-{index}"
    return {
        "document_identifier": f"csv-row-{index}",
        "event_id": event_id,
        "external_reference": f"external-csv-{index}",
        "source": "csv-test",
        "event_occurred_at": "2026-07-22T09:00:00-03:00",
        "event_received_at": "2026-07-22T12:01:00Z",
        "raw_payload": json.dumps({"contract_id": f"contract-csv-{index}"}),
        "evaluation_id": f"00000000-0000-0000-0000-{index:012d}",
        "subject_id": f"contract-csv-{index}",
        "evaluation_observed_at": "2026-07-22T12:00:00Z",
        "rules_engine_version": "rules-csv-1",
        "previous_speed": "500",
        "current_speed": "1000",
        "previous_plan_modality": "standard",
        "current_plan_modality": "standard",
        "previous_mesh_enabled": "false",
        "current_mesh_enabled": "false",
        "previous_additionals": "[]",
        "current_additionals": "[]",
        "previous_recurring_value": "89.90",
        "current_recurring_value": "99.90",
        "ticket_id": f"ticket-csv-{index}",
        "support_agent_id": "employee-1",
        "ticket_author_id": "employee-1",
        "duplicate_author_detected": "false",
        "ticket_linked_to_plan_change": "true",
        "change_marked_administrative": "false",
        "change_marked_corrective": "false",
        "conflicting_authorship_evidence_found": "false",
        "financial_snapshot_present": "true",
        "payment_evaluated_at": "2026-07-22T12:00:00Z",
        "invoice_id": f"invoice-csv-{index}",
        "invoice_due_date": "2026-07-10",
        "invoice_paid_at": "2026-07-11T12:00:00Z",
        "invoice_status": "paid",
        "invoice_recurring_amount": "99.90",
        "expected_recurring_amount": "99.90",
        "invoice_linked_to_event": "true",
        "is_first_new_value_invoice": "true",
        "first_invoice_candidate_count": "1",
        "already_validated_event_ids": "[]",
        "financial_reference_ids": json.dumps([f"invoice-csv-{index}"]),
        "has_link_conflict": "false",
        "has_duplicate_invoice_event_link": "false",
        "has_inconsistent_financial_input": "false",
        "payment_validation_reference": f"payment:{event_id}",
        "previous_remuneration_recurring_amount": "89.90",
        "new_remuneration_recurring_amount": "99.90",
        "full_new_plan_amount": "99.90",
        "additional_type": "",
        "renews_loyalty": "true",
        "commercial_reference_ids": json.dumps([f"contract-change-{index}"]),
        "calculation_reference_ids": json.dumps([f"calculation-input-{index}"]),
        "has_commercial_classification_conflict": "false",
        "has_inconsistent_remuneration_input": "false",
        "beneficiary_id": "employee-1",
        "posted_at": "2026-07-22T12:05:00Z",
        "posting_reference": f"posting:{event_id}",
        "source_reference_ids": json.dumps(
            [f"invoice-csv-{index}", f"ticket-csv-{index}"]
        ),
        "remuneration_calculation_reference": f"calculation:{event_id}",
        "has_ledger_reference_conflict": "false",
        "has_inconsistent_posting_input": "false",
    }


def csv_text(
    rows: list[dict[str, str]],
    *,
    columns: tuple[str, ...] = CSV_COLUMNS,
) -> str:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=columns, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue()
