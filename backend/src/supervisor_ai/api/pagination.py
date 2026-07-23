import base64
import binascii
import json
from datetime import UTC, datetime

from supervisor_ai.application import (
    CollaboratorFinancialTimelineCursorPosition,
    CommercialEventCursorPosition,
    ProcessingRunCursorPosition,
)

_CURSOR_VERSION = 1
_CURSOR_FIELDS = {"v", "occurred_at", "event_id"}
_TIMELINE_CURSOR_FIELDS = {"v", "posted_at", "ledger_entry_id"}
_PROCESSING_RUN_CURSOR_FIELDS = {"v", "started_at", "processing_run_id"}


class InvalidPaginationCursor(ValueError):
    """Cursor HTTP ausente, corrompido ou incompatível."""


def encode_cursor(position: CommercialEventCursorPosition) -> str:
    return _encode_payload(
        {
        "v": _CURSOR_VERSION,
        "occurred_at": position.occurred_at.astimezone(UTC).isoformat().replace(
            "+00:00", "Z"
        ),
        "event_id": position.event_id,
        }
    )


def decode_cursor(value: str) -> CommercialEventCursorPosition:
    payload = _decode_payload(value, _CURSOR_FIELDS)
    occurred_at = payload["occurred_at"]
    event_id = payload["event_id"]
    if not isinstance(occurred_at, str) or not isinstance(event_id, str):
        raise InvalidPaginationCursor("cursor field types are invalid")
    try:
        parsed_at = datetime.fromisoformat(occurred_at.replace("Z", "+00:00"))
        position = CommercialEventCursorPosition(parsed_at, event_id)
    except ValueError as error:
        raise InvalidPaginationCursor("cursor values are invalid") from error
    if parsed_at.tzinfo is None or parsed_at.utcoffset() is None:
        raise InvalidPaginationCursor("cursor timestamp must be timezone-aware")
    return CommercialEventCursorPosition(
        occurred_at=parsed_at.astimezone(UTC),
        event_id=position.event_id,
    )


def encode_timeline_cursor(
    position: CollaboratorFinancialTimelineCursorPosition,
) -> str:
    return _encode_payload(
        {
            "v": _CURSOR_VERSION,
            "posted_at": position.posted_at.astimezone(UTC).isoformat().replace(
                "+00:00", "Z"
            ),
            "ledger_entry_id": position.ledger_entry_id,
        }
    )


def decode_timeline_cursor(
    value: str,
) -> CollaboratorFinancialTimelineCursorPosition:
    payload = _decode_payload(value, _TIMELINE_CURSOR_FIELDS)
    posted_at = payload["posted_at"]
    ledger_entry_id = payload["ledger_entry_id"]
    if not isinstance(posted_at, str) or not isinstance(ledger_entry_id, str):
        raise InvalidPaginationCursor("cursor field types are invalid")
    try:
        parsed_at = datetime.fromisoformat(posted_at.replace("Z", "+00:00"))
        position = CollaboratorFinancialTimelineCursorPosition(
            parsed_at, ledger_entry_id
        )
    except ValueError as error:
        raise InvalidPaginationCursor("cursor values are invalid") from error
    if parsed_at.tzinfo is None or parsed_at.utcoffset() is None:
        raise InvalidPaginationCursor("cursor timestamp must be timezone-aware")
    return CollaboratorFinancialTimelineCursorPosition(
        posted_at=parsed_at.astimezone(UTC),
        ledger_entry_id=position.ledger_entry_id,
    )


def encode_processing_run_cursor(position: ProcessingRunCursorPosition) -> str:
    return _encode_payload(
        {
            "v": _CURSOR_VERSION,
            "started_at": position.started_at.astimezone(UTC).isoformat().replace(
                "+00:00", "Z"
            ),
            "processing_run_id": position.processing_run_id,
        }
    )


def decode_processing_run_cursor(value: str) -> ProcessingRunCursorPosition:
    payload = _decode_payload(value, _PROCESSING_RUN_CURSOR_FIELDS)
    started_at = payload["started_at"]
    processing_run_id = payload["processing_run_id"]
    if not isinstance(started_at, str) or not isinstance(processing_run_id, str):
        raise InvalidPaginationCursor("cursor field types are invalid")
    try:
        parsed_at = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
        position = ProcessingRunCursorPosition(parsed_at, processing_run_id)
    except ValueError as error:
        raise InvalidPaginationCursor("cursor values are invalid") from error
    if parsed_at.tzinfo is None or parsed_at.utcoffset() is None:
        raise InvalidPaginationCursor("cursor timestamp must be timezone-aware")
    return ProcessingRunCursorPosition(
        started_at=parsed_at.astimezone(UTC),
        processing_run_id=position.processing_run_id,
    )


def _encode_payload(payload: dict[str, object]) -> str:
    serialized = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode()
    return base64.urlsafe_b64encode(serialized).decode().rstrip("=")


def _decode_payload(value: str, expected_fields: set[str]) -> dict[str, object]:
    if not value:
        raise InvalidPaginationCursor("cursor must not be empty")
    try:
        padding = "=" * (-len(value) % 4)
        decoded = base64.b64decode(
            value + padding,
            altchars=b"-_",
            validate=True,
        )
        payload = json.loads(decoded)
    except (binascii.Error, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise InvalidPaginationCursor("cursor encoding is invalid") from error
    if not isinstance(payload, dict) or set(payload) != expected_fields:
        raise InvalidPaginationCursor("cursor structure is invalid")
    if type(payload["v"]) is not int or payload["v"] != _CURSOR_VERSION:
        raise InvalidPaginationCursor("cursor version is invalid")
    return payload
