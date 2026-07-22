from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from supervisor_ai.infrastructure.importing.mapper import JsonImportDocumentMapper
from supervisor_ai.infrastructure.importing.parser import parse_json_text
from supervisor_ai.infrastructure.importing.schema import JsonImportDocumentValidator
from supervisor_ai.rules_engine import ContractualEvidenceName
from tests.importing.factories import complete_document, document, evidence, json_text


def test_maps_public_contracts_without_silent_string_coercion() -> None:
    value = document()
    evaluation = value["evaluation"]
    assert isinstance(evaluation, dict)
    evaluation["evidence"] = [
        evidence("speed", "previous_speed", 500),
        evidence("items", "current_additionals", ["IP", "Watch"]),
        evidence("money", "current_recurring_value", 99.90),
    ]
    validated = JsonImportDocumentValidator().validate(
        parse_json_text(json_text(value))
    )

    command = JsonImportDocumentMapper().map(validated)

    assert command.event.occurred_at == datetime(2026, 7, 21, 13, 0, tzinfo=UTC)
    assert command.event.received_at == datetime(2026, 7, 21, 13, 1, tzinfo=UTC)
    event_document = value["event"]
    assert isinstance(event_document, dict)
    assert command.event.raw_payload == event_document["raw_payload"]
    assert command.evaluation_context.evaluation_id == UUID(
        "00000000-0000-0000-0000-000000000001"
    )
    assert tuple(item.evidence_id for item in command.evaluation_context.evidence) == (
        "speed",
        "items",
        "money",
    )
    mapped = command.evaluation_context.evidence
    assert mapped[0].name == ContractualEvidenceName.PREVIOUS_SPEED
    assert mapped[0].value == 500
    assert type(mapped[0].value) is int
    assert mapped[1].value == ("IP", "Watch")
    assert mapped[2].value == Decimal("99.9")
    assert isinstance(mapped[2].value, Decimal)


def test_maps_financial_snapshot_with_precise_decimal_and_aware_dates() -> None:
    validated = JsonImportDocumentValidator().validate(
        parse_json_text(json_text(complete_document()))
    )
    command = JsonImportDocumentMapper().map(validated)
    assert command.financial_snapshot is not None
    payment = command.financial_snapshot.payment
    assert payment.invoice_recurring_amount == Decimal("99.90")
    assert isinstance(payment.invoice_recurring_amount, Decimal)
    assert payment.invoice_paid_at == datetime(2026, 7, 11, 12, tzinfo=UTC)
    assert command.financial_snapshot.posting.posted_at == datetime(
        2026, 7, 21, 13, 5, tzinfo=UTC
    )


def test_maps_canonical_contractual_money_without_float() -> None:
    value = document()
    evaluation = value["evaluation"]
    assert isinstance(evaluation, dict)
    evaluation["evidence"] = [
        evidence("money", "current_recurring_value", "99.90")
    ]
    validated = JsonImportDocumentValidator().validate(
        parse_json_text(json_text(value))
    )
    command = JsonImportDocumentMapper().map(validated)
    mapped = command.evaluation_context.evidence[0].value
    assert mapped == Decimal("99.90")
    assert isinstance(mapped, Decimal)
