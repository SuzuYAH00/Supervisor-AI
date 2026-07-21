from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from supervisor_ai.application.persistence import JsonValue
from supervisor_ai.infrastructure.importing.errors import ImportValidationError
from supervisor_ai.rules_engine import ContractualEvidenceName

ROOT_FIELDS = frozenset({"event", "evaluation", "rules_engine_version"})
EVENT_FIELDS = frozenset(
    {"id", "external_reference", "source", "occurred_at", "received_at", "raw_payload"}
)
EVALUATION_FIELDS = frozenset(
    {"evaluation_id", "subject_id", "observed_at", "evidence"}
)
EVIDENCE_FIELDS = frozenset({"id", "name", "value", "observed_at"})


@dataclass(frozen=True, slots=True)
class ValidatedEvidenceDocument:
    id: str
    name: ContractualEvidenceName
    value: JsonValue
    observed_at: str


@dataclass(frozen=True, slots=True)
class ValidatedEventDocument:
    id: str
    external_reference: str
    source: str
    occurred_at: str
    received_at: str
    raw_payload: dict[str, JsonValue]


@dataclass(frozen=True, slots=True)
class ValidatedEvaluationDocument:
    evaluation_id: str
    subject_id: str
    observed_at: str
    evidence: tuple[ValidatedEvidenceDocument, ...]


@dataclass(frozen=True, slots=True)
class ValidatedImportDocument:
    event: ValidatedEventDocument
    evaluation: ValidatedEvaluationDocument
    rules_engine_version: str


class JsonImportDocumentValidator:
    def validate(self, value: object) -> ValidatedImportDocument:
        root = _require_object(value, "$")
        _require_closed_schema(root, ROOT_FIELDS, "$")
        event = self._event(_required(root, "event", "$"))
        evaluation = self._evaluation(_required(root, "evaluation", "$"))
        version = _required_string(root, "rules_engine_version", "$")
        return ValidatedImportDocument(event, evaluation, version)

    @staticmethod
    def _event(value: object) -> ValidatedEventDocument:
        document = _require_object(value, "event")
        _require_closed_schema(document, EVENT_FIELDS, "event")
        raw_payload_value = _required(document, "raw_payload", "event")
        raw_payload = _require_json_object(raw_payload_value, "event.raw_payload")
        occurred_at = _required_string(document, "occurred_at", "event")
        received_at = _required_string(document, "received_at", "event")
        _validate_datetime(occurred_at, "event.occurred_at")
        _validate_datetime(received_at, "event.received_at")
        return ValidatedEventDocument(
            id=_required_string(document, "id", "event"),
            external_reference=_required_string(
                document, "external_reference", "event"
            ),
            source=_required_string(document, "source", "event"),
            occurred_at=occurred_at,
            received_at=received_at,
            raw_payload=raw_payload,
        )

    def _evaluation(self, value: object) -> ValidatedEvaluationDocument:
        document = _require_object(value, "evaluation")
        _require_closed_schema(document, EVALUATION_FIELDS, "evaluation")
        evaluation_id = _required_string(document, "evaluation_id", "evaluation")
        _validate_uuid(evaluation_id, "evaluation.evaluation_id")
        observed_at = _required_string(document, "observed_at", "evaluation")
        _validate_datetime(observed_at, "evaluation.observed_at")
        evidence_value = _required(document, "evidence", "evaluation")
        if not isinstance(evidence_value, list):
            raise ImportValidationError("evaluation.evidence: expected array")
        evidence = tuple(
            self._evidence(item, index) for index, item in enumerate(evidence_value)
        )
        identifiers = tuple(item.id for item in evidence)
        if len(identifiers) != len(set(identifiers)):
            duplicate = next(
                item for item in identifiers if identifiers.count(item) > 1
            )
            raise ImportValidationError(
                f"evaluation.evidence: duplicate evidence id {duplicate!r}"
            )
        return ValidatedEvaluationDocument(
            evaluation_id=evaluation_id,
            subject_id=_required_string(document, "subject_id", "evaluation"),
            observed_at=observed_at,
            evidence=evidence,
        )

    @staticmethod
    def _evidence(value: object, index: int) -> ValidatedEvidenceDocument:
        path = f"evaluation.evidence[{index}]"
        document = _require_object(value, path)
        _require_closed_schema(document, EVIDENCE_FIELDS, path)
        name_value = _required_string(document, "name", path)
        try:
            name = ContractualEvidenceName(name_value)
        except ValueError as error:
            raise ImportValidationError(
                f"{path}.name: unknown evidence name"
            ) from error
        observed_at = _required_string(document, "observed_at", path)
        _validate_datetime(observed_at, f"{path}.observed_at")
        raw_value = _required(document, "value", path)
        json_value = _require_json_value(raw_value, f"{path}.value")
        _validate_evidence_value(name, json_value, f"{path}.value")
        return ValidatedEvidenceDocument(
            id=_required_string(document, "id", path),
            name=name,
            value=json_value,
            observed_at=observed_at,
        )


def _required(document: dict[str, object], field: str, path: str) -> object:
    if field not in document:
        field_path = field if path == "$" else f"{path}.{field}"
        raise ImportValidationError(f"{field_path}: required field is missing")
    return document[field]


def _required_string(document: dict[str, object], field: str, path: str) -> str:
    field_path = field if path == "$" else f"{path}.{field}"
    value = _required(document, field, path)
    if type(value) is not str:
        raise ImportValidationError(f"{field_path}: expected string")
    if not value:
        raise ImportValidationError(f"{field_path}: must not be empty")
    return value


def _require_object(value: object, path: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ImportValidationError(f"{path}: expected object")
    return value


def _require_closed_schema(
    document: dict[str, object], allowed: frozenset[str], path: str
) -> None:
    unknown = sorted(set(document) - allowed)
    if unknown:
        field_path = unknown[0] if path == "$" else f"{path}.{unknown[0]}"
        raise ImportValidationError(f"{field_path}: unknown field")
    missing = sorted(allowed - set(document))
    if missing:
        field_path = missing[0] if path == "$" else f"{path}.{missing[0]}"
        raise ImportValidationError(f"{field_path}: required field is missing")


def _require_json_object(value: object, path: str) -> dict[str, JsonValue]:
    if not isinstance(value, dict):
        raise ImportValidationError(f"{path}: expected object")
    return {
        key: _require_json_value(item, f"{path}.{key}")
        for key, item in value.items()
    }


def _require_json_value(value: object, path: str) -> JsonValue:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return value
    if isinstance(value, list):
        return [
            _require_json_value(item, f"{path}[{index}]")
            for index, item in enumerate(value)
        ]
    if isinstance(value, dict):
        return {
            key: _require_json_value(item, f"{path}.{key}")
            for key, item in value.items()
        }
    raise ImportValidationError(f"{path}: unsupported JSON value")


def _validate_uuid(value: str, path: str) -> None:
    try:
        UUID(value)
    except ValueError as error:
        raise ImportValidationError(f"{path}: invalid UUID") from error


def _parse_datetime(value: str, path: str) -> datetime:
    candidate = f"{value[:-1]}+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError as error:
        raise ImportValidationError(f"{path}: invalid ISO 8601 datetime") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ImportValidationError(f"{path}: timezone offset is required")
    return parsed


def _validate_datetime(value: str, path: str) -> None:
    _parse_datetime(value, path)


def _validate_evidence_value(
    name: ContractualEvidenceName, value: JsonValue, path: str
) -> None:
    if name in {
        ContractualEvidenceName.PREVIOUS_SPEED,
        ContractualEvidenceName.CURRENT_SPEED,
    }:
        valid = type(value) is int
    elif name in {
        ContractualEvidenceName.PREVIOUS_PLAN_MODALITY,
        ContractualEvidenceName.CURRENT_PLAN_MODALITY,
    }:
        valid = type(value) is str
    elif name in {
        ContractualEvidenceName.PREVIOUS_MESH_ENABLED,
        ContractualEvidenceName.CURRENT_MESH_ENABLED,
    }:
        valid = type(value) is bool
    elif name in {
        ContractualEvidenceName.PREVIOUS_ADDITIONALS,
        ContractualEvidenceName.CURRENT_ADDITIONALS,
    }:
        valid = (
            isinstance(value, list)
            and all(type(item) is str for item in value)
            and len(value) == len(set(value))
        )
    else:
        valid = type(value) in {int, float}
    if not valid:
        raise ImportValidationError(f"{path}: incompatible evidence value")


parse_datetime = _parse_datetime
