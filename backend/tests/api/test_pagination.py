import base64
import json
from datetime import UTC, datetime, timedelta, timezone

import pytest

from supervisor_ai.api.pagination import (
    InvalidPaginationCursor,
    decode_cursor,
    encode_cursor,
)
from supervisor_ai.application import CommercialEventCursorPosition

POSITION = CommercialEventCursorPosition(
    datetime(2026, 7, 22, 12, tzinfo=UTC), "event-1"
)


def encoded(payload: object) -> str:
    return base64.urlsafe_b64encode(
        json.dumps(payload, separators=(",", ":")).encode()
    ).decode().rstrip("=")


def test_cursor_round_trip_is_canonical_and_url_safe() -> None:
    value = encode_cursor(POSITION)
    assert decode_cursor(value) == POSITION
    assert "=" not in value
    assert all(character.isalnum() or character in "-_" for character in value)


def test_cursor_normalizes_aware_timestamp_to_utc() -> None:
    position = CommercialEventCursorPosition(
        datetime(2026, 7, 22, 9, tzinfo=timezone(-timedelta(hours=3))),
        "event-1",
    )
    assert decode_cursor(encode_cursor(position)) == POSITION


@pytest.mark.parametrize(
    "value",
    [
        "",
        "***",
        encoded("not-an-object"),
        encoded({"v": 1, "occurred_at": "2026-07-22T12:00:00Z"}),
        encoded(
            {
                "v": 1,
                "occurred_at": "2026-07-22T12:00:00Z",
                "event_id": "event-1",
                "extra": True,
            }
        ),
        encoded(
            {"v": 2, "occurred_at": "2026-07-22T12:00:00Z", "event_id": "event-1"}
        ),
        encoded(
            {
                "v": 1,
                "occurred_at": "not-a-date",
                "event_id": "event-1",
            }
        ),
        encoded(
            {
                "v": 1,
                "occurred_at": "2026-07-22T12:00:00",
                "event_id": "event-1",
            }
        ),
        encoded({"v": 1, "occurred_at": 1, "event_id": "event-1"}),
        encoded({"v": 1, "occurred_at": "2026-07-22T12:00:00Z", "event_id": ""}),
        encoded(
            {
                "v": 1,
                "occurred_at": "2026-07-22T12:00:00Z",
                "event_id": "x" * 129,
            }
        ),
    ],
)
def test_invalid_cursor_shapes_are_rejected(value: str) -> None:
    with pytest.raises(InvalidPaginationCursor):
        decode_cursor(value)
