import re
from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID

from supervisor_ai.application.persistence import JsonValue
from supervisor_ai.infrastructure.importing.errors import ImportValidationError
from supervisor_ai.rules_engine import (
    ContractualEvidenceName,
    InvoicePaymentStatus,
    NonLoyaltyAdditionalType,
    OperationalFactName,
)

type EvidenceName = ContractualEvidenceName | OperationalFactName

ROOT_FIELDS = frozenset(
    {"event", "evaluation", "rules_engine_version", "financial_snapshot"}
)
EVENT_FIELDS = frozenset(
    {"id", "external_reference", "source", "occurred_at", "received_at", "raw_payload"}
)
EVALUATION_FIELDS = frozenset(
    {"evaluation_id", "subject_id", "observed_at", "evidence"}
)
EVIDENCE_FIELDS = frozenset({"id", "name", "value", "observed_at"})
FINANCIAL_SNAPSHOT_FIELDS = frozenset({"payment", "remuneration", "posting"})
PAYMENT_FIELDS = frozenset(
    {
        "evaluated_at",
        "invoice_id",
        "invoice_due_date",
        "invoice_paid_at",
        "invoice_status",
        "invoice_recurring_amount",
        "expected_recurring_amount",
        "invoice_linked_to_event",
        "is_first_new_value_invoice",
        "first_invoice_candidate_count",
        "already_validated_event_ids",
        "financial_reference_ids",
        "has_link_conflict",
        "has_duplicate_invoice_event_link",
        "has_inconsistent_financial_input",
    }
)
REMUNERATION_FIELDS = frozenset(
    {
        "payment_validation_reference",
        "previous_recurring_amount",
        "new_recurring_amount",
        "full_new_plan_amount",
        "additional_type",
        "renews_loyalty",
        "commercial_reference_ids",
        "calculation_reference_ids",
        "has_commercial_classification_conflict",
        "has_inconsistent_input",
    }
)
POSTING_FIELDS = frozenset(
    {
        "beneficiary_id",
        "posted_at",
        "posting_reference",
        "source_reference_ids",
        "remuneration_calculation_reference",
        "has_ledger_reference_conflict",
        "has_inconsistent_input",
    }
)
DECIMAL_PATTERN = re.compile(r"(?:0|[1-9][0-9]*)(?:\.[0-9]+)?\Z")


@dataclass(frozen=True, slots=True)
class ValidatedEvidenceDocument:
    id: str
    name: EvidenceName
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
class ValidatedPaymentDocument:
    evaluated_at: str
    invoice_id: str | None
    invoice_due_date: str | None
    invoice_paid_at: str | None
    invoice_status: InvoicePaymentStatus | None
    invoice_recurring_amount: str | None
    expected_recurring_amount: str | None
    invoice_linked_to_event: bool | None
    is_first_new_value_invoice: bool | None
    first_invoice_candidate_count: int | None
    already_validated_event_ids: tuple[str, ...]
    financial_reference_ids: tuple[str, ...]
    has_link_conflict: bool
    has_duplicate_invoice_event_link: bool
    has_inconsistent_financial_input: bool


@dataclass(frozen=True, slots=True)
class ValidatedRemunerationDocument:
    payment_validation_reference: str
    previous_recurring_amount: str | None
    new_recurring_amount: str | None
    full_new_plan_amount: str | None
    additional_type: NonLoyaltyAdditionalType | None
    renews_loyalty: bool | None
    commercial_reference_ids: tuple[str, ...]
    calculation_reference_ids: tuple[str, ...]
    has_commercial_classification_conflict: bool
    has_inconsistent_input: bool


@dataclass(frozen=True, slots=True)
class ValidatedPostingDocument:
    beneficiary_id: str | None
    posted_at: str | None
    posting_reference: str | None
    source_reference_ids: tuple[str, ...]
    remuneration_calculation_reference: str | None
    has_ledger_reference_conflict: bool
    has_inconsistent_input: bool


@dataclass(frozen=True, slots=True)
class ValidatedFinancialSnapshotDocument:
    payment: ValidatedPaymentDocument
    remuneration: ValidatedRemunerationDocument
    posting: ValidatedPostingDocument


@dataclass(frozen=True, slots=True)
class ValidatedImportDocument:
    event: ValidatedEventDocument
    evaluation: ValidatedEvaluationDocument
    rules_engine_version: str
    financial_snapshot: ValidatedFinancialSnapshotDocument | None = None


class JsonImportDocumentValidator:
    def validate(self, value: object) -> ValidatedImportDocument:
        root = _require_object(value, "$")
        _require_closed_schema(
            root, ROOT_FIELDS, "$", optional=frozenset({"financial_snapshot"})
        )
        event = self._event(_required(root, "event", "$"))
        evaluation = self._evaluation(_required(root, "evaluation", "$"))
        version = _required_string(root, "rules_engine_version", "$")
        snapshot_value = root.get("financial_snapshot")
        snapshot = (
            None
            if snapshot_value is None
            else self._financial_snapshot(snapshot_value)
        )
        return ValidatedImportDocument(event, evaluation, version, snapshot)

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
        name = _evidence_name(name_value)
        if name is None:
            raise ImportValidationError(
                f"{path}.name: unknown evidence name"
            )
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

    @staticmethod
    def _financial_snapshot(value: object) -> ValidatedFinancialSnapshotDocument:
        path = "financial_snapshot"
        document = _require_object(value, path)
        _require_closed_schema(document, FINANCIAL_SNAPSHOT_FIELDS, path)
        return ValidatedFinancialSnapshotDocument(
            payment=_payment(_required(document, "payment", path)),
            remuneration=_remuneration(
                _required(document, "remuneration", path)
            ),
            posting=_posting(_required(document, "posting", path)),
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
    document: dict[str, object],
    allowed: frozenset[str],
    path: str,
    *,
    optional: frozenset[str] = frozenset(),
) -> None:
    unknown = sorted(set(document) - allowed)
    if unknown:
        field_path = unknown[0] if path == "$" else f"{path}.{unknown[0]}"
        raise ImportValidationError(f"{field_path}: unknown field")
    missing = sorted(allowed - optional - set(document))
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
    name: EvidenceName, value: JsonValue, path: str
) -> None:
    if not isinstance(name, ContractualEvidenceName):
        if isinstance(value, dict):
            raise ImportValidationError(f"{path}: incompatible evidence value")
        return
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


def _evidence_name(value: str) -> EvidenceName | None:
    for enum_type in (ContractualEvidenceName, OperationalFactName):
        try:
            return enum_type(value)
        except ValueError:
            continue
    return None


def _payment(value: object) -> ValidatedPaymentDocument:
    path = "financial_snapshot.payment"
    document = _require_object(value, path)
    _require_closed_schema(document, PAYMENT_FIELDS, path)
    evaluated_at = _required_string(document, "evaluated_at", path)
    _validate_datetime(evaluated_at, f"{path}.evaluated_at")
    due_date = _optional_string(document, "invoice_due_date", path)
    if due_date is not None:
        _validate_date(due_date, f"{path}.invoice_due_date")
    paid_at = _optional_string(document, "invoice_paid_at", path)
    if paid_at is not None:
        _validate_datetime(paid_at, f"{path}.invoice_paid_at")
    candidate_count = _optional_int(
        document, "first_invoice_candidate_count", path
    )
    if candidate_count is not None and candidate_count < 0:
        raise ImportValidationError(
            f"{path}.first_invoice_candidate_count: must not be negative"
        )
    return ValidatedPaymentDocument(
        evaluated_at=evaluated_at,
        invoice_id=_optional_string(document, "invoice_id", path),
        invoice_due_date=due_date,
        invoice_paid_at=paid_at,
        invoice_status=_optional_enum(
            document, "invoice_status", path, InvoicePaymentStatus
        ),
        invoice_recurring_amount=_optional_money(
            document, "invoice_recurring_amount", path
        ),
        expected_recurring_amount=_optional_money(
            document, "expected_recurring_amount", path
        ),
        invoice_linked_to_event=_optional_bool(
            document, "invoice_linked_to_event", path
        ),
        is_first_new_value_invoice=_optional_bool(
            document, "is_first_new_value_invoice", path
        ),
        first_invoice_candidate_count=candidate_count,
        already_validated_event_ids=_string_array(
            document, "already_validated_event_ids", path
        ),
        financial_reference_ids=_string_array(
            document, "financial_reference_ids", path
        ),
        has_link_conflict=_required_bool(document, "has_link_conflict", path),
        has_duplicate_invoice_event_link=_required_bool(
            document, "has_duplicate_invoice_event_link", path
        ),
        has_inconsistent_financial_input=_required_bool(
            document, "has_inconsistent_financial_input", path
        ),
    )


def _remuneration(value: object) -> ValidatedRemunerationDocument:
    path = "financial_snapshot.remuneration"
    document = _require_object(value, path)
    _require_closed_schema(document, REMUNERATION_FIELDS, path)
    return ValidatedRemunerationDocument(
        payment_validation_reference=_required_string(
            document, "payment_validation_reference", path
        ),
        previous_recurring_amount=_optional_money(
            document, "previous_recurring_amount", path
        ),
        new_recurring_amount=_optional_money(
            document, "new_recurring_amount", path
        ),
        full_new_plan_amount=_optional_money(
            document, "full_new_plan_amount", path
        ),
        additional_type=_optional_enum(
            document, "additional_type", path, NonLoyaltyAdditionalType
        ),
        renews_loyalty=_optional_bool(document, "renews_loyalty", path),
        commercial_reference_ids=_string_array(
            document, "commercial_reference_ids", path
        ),
        calculation_reference_ids=_string_array(
            document, "calculation_reference_ids", path
        ),
        has_commercial_classification_conflict=_required_bool(
            document, "has_commercial_classification_conflict", path
        ),
        has_inconsistent_input=_required_bool(
            document, "has_inconsistent_input", path
        ),
    )


def _posting(value: object) -> ValidatedPostingDocument:
    path = "financial_snapshot.posting"
    document = _require_object(value, path)
    _require_closed_schema(document, POSTING_FIELDS, path)
    posted_at = _optional_string(document, "posted_at", path)
    if posted_at is not None:
        _validate_datetime(posted_at, f"{path}.posted_at")
    return ValidatedPostingDocument(
        beneficiary_id=_optional_string(document, "beneficiary_id", path),
        posted_at=posted_at,
        posting_reference=_optional_string(document, "posting_reference", path),
        source_reference_ids=_string_array(
            document, "source_reference_ids", path
        ),
        remuneration_calculation_reference=_optional_string(
            document, "remuneration_calculation_reference", path
        ),
        has_ledger_reference_conflict=_required_bool(
            document, "has_ledger_reference_conflict", path
        ),
        has_inconsistent_input=_required_bool(
            document, "has_inconsistent_input", path
        ),
    )


def _optional_string(
    document: dict[str, object], field: str, path: str
) -> str | None:
    value = _required(document, field, path)
    if value is None:
        return None
    if type(value) is not str:
        raise ImportValidationError(f"{path}.{field}: expected string or null")
    if not value:
        raise ImportValidationError(f"{path}.{field}: must not be empty")
    return value


def _required_bool(document: dict[str, object], field: str, path: str) -> bool:
    value = _required(document, field, path)
    if type(value) is not bool:
        raise ImportValidationError(f"{path}.{field}: expected boolean")
    return value


def _optional_bool(
    document: dict[str, object], field: str, path: str
) -> bool | None:
    value = _required(document, field, path)
    if value is None:
        return None
    if type(value) is not bool:
        raise ImportValidationError(f"{path}.{field}: expected boolean or null")
    return value


def _optional_int(
    document: dict[str, object], field: str, path: str
) -> int | None:
    value = _required(document, field, path)
    if value is None:
        return None
    if type(value) is not int:
        raise ImportValidationError(f"{path}.{field}: expected integer or null")
    return value


def _optional_money(
    document: dict[str, object], field: str, path: str
) -> str | None:
    value = _required(document, field, path)
    if value is None:
        return None
    if type(value) is not str or DECIMAL_PATTERN.fullmatch(value) is None:
        raise ImportValidationError(
            f"{path}.{field}: expected canonical non-negative decimal string or null"
        )
    return value


def _string_array(
    document: dict[str, object], field: str, path: str
) -> tuple[str, ...]:
    value = _required(document, field, path)
    if not isinstance(value, list) or any(type(item) is not str for item in value):
        raise ImportValidationError(f"{path}.{field}: expected array of strings")
    if any(not item for item in value):
        raise ImportValidationError(f"{path}.{field}: values must not be empty")
    return tuple(value)


def _optional_enum[E](
    document: dict[str, object], field: str, path: str, enum_type: type[E]
) -> E | None:
    value = _required(document, field, path)
    if value is None:
        return None
    if type(value) is not str:
        raise ImportValidationError(f"{path}.{field}: expected string or null")
    try:
        return enum_type(value)
    except ValueError as error:
        raise ImportValidationError(f"{path}.{field}: invalid enum value") from error


def _validate_date(value: str, path: str) -> None:
    try:
        date.fromisoformat(value)
    except ValueError as error:
        raise ImportValidationError(f"{path}: invalid ISO 8601 date") from error
