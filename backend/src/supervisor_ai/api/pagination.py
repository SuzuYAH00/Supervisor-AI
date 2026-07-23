import base64
import binascii
import json
from datetime import UTC, datetime

from supervisor_ai.application import CommercialEventCursorPosition

_CURSOR_VERSION = 1
_CURSOR_FIELDS = {"v", "occurred_at", "event_id"}


class InvalidPaginationCursor(ValueError):
    """Cursor HTTP ausente, corrompido ou incompatível."""


def encode_cursor(position: CommercialEventCursorPosition) -> str:
    payload = {
        "v": _CURSOR_VERSION,
        "occurred_at": position.occurred_at.astimezone(UTC).isoformat().replace(
            "+00:00", "Z"
        ),
        "event_id": position.event_id,
    }
    serialized = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode()
    return base64.urlsafe_b64encode(serialized).decode().rstrip("=")


def decode_cursor(value: str) -> CommercialEventCursorPosition:
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
    if not isinstance(payload, dict) or set(payload) != _CURSOR_FIELDS:
        raise InvalidPaginationCursor("cursor structure is invalid")
    if type(payload["v"]) is not int or payload["v"] != _CURSOR_VERSION:
        raise InvalidPaginationCursor("cursor version is invalid")
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
