from copy import deepcopy

import pytest

from supervisor_ai.infrastructure.importing import ImportValidationError
from supervisor_ai.infrastructure.importing.parser import parse_json_text
from supervisor_ai.infrastructure.importing.schema import JsonImportDocumentValidator
from tests.importing.factories import document, evidence, json_text


def validate(value: dict[str, object] | None = None):
    return JsonImportDocumentValidator().validate(
        parse_json_text(json_text(value or document()))
    )


def test_accepts_minimal_valid_document() -> None:
    result = validate()
    assert result.event.id == "event-json-1"
    assert result.evaluation.evidence == ()


def test_rejects_root_other_than_object() -> None:
    with pytest.raises(ImportValidationError, match=r"\$: expected object"):
        JsonImportDocumentValidator().validate([])


def test_rejects_missing_required_field_with_path() -> None:
    value = document()
    del value["event"]
    with pytest.raises(ImportValidationError, match="event: required field"):
        validate(value)


def test_rejects_unknown_field_with_path() -> None:
    value = document()
    value["unknown"] = True
    with pytest.raises(ImportValidationError, match="unknown: unknown field"):
        validate(value)


def test_rejects_incorrect_type() -> None:
    value = document()
    event_document = value["event"]
    assert isinstance(event_document, dict)
    event_document["source"] = 10
    with pytest.raises(ImportValidationError, match="event.source: expected string"):
        validate(value)


def test_rejects_empty_required_string() -> None:
    value = document()
    event_document = value["event"]
    assert isinstance(event_document, dict)
    event_document["external_reference"] = ""
    with pytest.raises(
        ImportValidationError, match="event.external_reference: must not be empty"
    ):
        validate(value)


def test_rejects_invalid_uuid() -> None:
    value = document()
    evaluation = value["evaluation"]
    assert isinstance(evaluation, dict)
    evaluation["evaluation_id"] = "not-a-uuid"
    with pytest.raises(
        ImportValidationError, match="evaluation.evaluation_id: invalid UUID"
    ):
        validate(value)


@pytest.mark.parametrize(
    ("datetime_value", "message"),
    [
        ("not-a-date", "invalid ISO 8601 datetime"),
        ("2026-07-21T13:00:00", "timezone offset is required"),
    ],
)
def test_rejects_invalid_or_naive_datetime(
    datetime_value: str, message: str
) -> None:
    value = document()
    evaluation = value["evaluation"]
    assert isinstance(evaluation, dict)
    evaluation["observed_at"] = datetime_value
    with pytest.raises(
        ImportValidationError, match=f"evaluation.observed_at: {message}"
    ):
        validate(value)


def test_rejects_raw_payload_other_than_object() -> None:
    value = document()
    event_document = value["event"]
    assert isinstance(event_document, dict)
    event_document["raw_payload"] = []
    with pytest.raises(
        ImportValidationError, match="event.raw_payload: expected object"
    ):
        validate(value)


def test_rejects_evidence_other_than_array() -> None:
    value = document()
    evaluation = value["evaluation"]
    assert isinstance(evaluation, dict)
    evaluation["evidence"] = {}
    with pytest.raises(
        ImportValidationError, match="evaluation.evidence: expected array"
    ):
        validate(value)


def test_rejects_unknown_evidence_name() -> None:
    value = document()
    evaluation = value["evaluation"]
    assert isinstance(evaluation, dict)
    evaluation["evidence"] = [evidence("evidence-1", "unknown", 500)]
    with pytest.raises(
        ImportValidationError,
        match=r"evaluation.evidence\[0\].name: unknown evidence name",
    ):
        validate(value)


@pytest.mark.parametrize(
    ("name", "invalid_value"),
    [
        ("previous_speed", "500"),
        ("previous_mesh_enabled", "true"),
        ("previous_additionals", ["IP", 10]),
        ("previous_recurring_value", "89.90"),
    ],
)
def test_rejects_incompatible_evidence_value(
    name: str, invalid_value: object
) -> None:
    value = document()
    evaluation = value["evaluation"]
    assert isinstance(evaluation, dict)
    evaluation["evidence"] = [evidence("evidence-1", name, invalid_value)]
    with pytest.raises(
        ImportValidationError,
        match=r"evaluation.evidence\[0\].value: incompatible evidence value",
    ):
        validate(value)


def test_rejects_duplicate_evidence_ids() -> None:
    value = document()
    evaluation = value["evaluation"]
    assert isinstance(evaluation, dict)
    evaluation["evidence"] = [
        evidence("same", "previous_speed", 500),
        evidence("same", "current_speed", 1000),
    ]
    with pytest.raises(ImportValidationError, match="duplicate evidence id 'same'"):
        validate(value)


def test_rejects_empty_rules_engine_version() -> None:
    value = document()
    value["rules_engine_version"] = ""
    with pytest.raises(
        ImportValidationError, match="rules_engine_version: must not be empty"
    ):
        validate(value)


def test_input_document_is_not_mutated() -> None:
    value = document()
    original = deepcopy(value)
    validate(value)
    assert value == original
