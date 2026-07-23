import base64
import json
from datetime import UTC, datetime, timedelta, timezone

import pytest

from supervisor_ai.api.pagination import (
    InvalidPaginationCursor,
    decode_cursor,
    decode_processing_run_cursor,
    decode_timeline_cursor,
    encode_cursor,
    encode_processing_run_cursor,
    encode_timeline_cursor,
)
from supervisor_ai.application import (
    CollaboratorFinancialTimelineCursorPosition,
    CommercialEventCursorPosition,
    ProcessingRunCursorPosition,
)

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


def test_timeline_cursor_round_trip_is_url_safe_and_normalizes_utc() -> None:
    position = CollaboratorFinancialTimelineCursorPosition(
        datetime(2026, 7, 22, 9, tzinfo=timezone(-timedelta(hours=3))),
        "ledger-1",
    )
    value = encode_timeline_cursor(position)
    assert "=" not in value
    assert decode_timeline_cursor(value) == (
        CollaboratorFinancialTimelineCursorPosition(
            datetime(2026, 7, 22, 12, tzinfo=UTC),
            "ledger-1",
        )
    )


@pytest.mark.parametrize(
    "value",
    [
        "",
        "***",
        encoded({"v": 2, "posted_at": "2026-07-22T12:00:00Z", "ledger_entry_id": "x"}),
        encoded({"v": 1, "posted_at": "invalid", "ledger_entry_id": "x"}),
        encoded({"v": 1, "posted_at": "2026-07-22T12:00:00", "ledger_entry_id": "x"}),
        encoded({"v": 1, "posted_at": "2026-07-22T12:00:00Z"}),
        encoded(
            {
                "v": 1,
                "posted_at": "2026-07-22T12:00:00Z",
                "ledger_entry_id": "",
            }
        ),
        encoded(
            {
                "v": 1,
                "posted_at": "2026-07-22T12:00:00Z",
                "ledger_entry_id": "x" * 256,
            }
        ),
        encoded(
            {
                "v": 1,
                "posted_at": "2026-07-22T12:00:00Z",
                "ledger_entry_id": "x",
                "extra": True,
            }
        ),
    ],
)
def test_invalid_timeline_cursor_is_rejected(value: str) -> None:
    with pytest.raises(InvalidPaginationCursor):
        decode_timeline_cursor(value)


def test_processing_run_cursor_round_trip_is_url_safe_and_normalizes_utc() -> None:
    position = ProcessingRunCursorPosition(
        datetime(2026, 7, 22, 9, tzinfo=timezone(-timedelta(hours=3))),
        "run-1",
    )
    value = encode_processing_run_cursor(position)
    assert "=" not in value
    assert decode_processing_run_cursor(value) == ProcessingRunCursorPosition(
        datetime(2026, 7, 22, 12, tzinfo=UTC),
        "run-1",
    )


@pytest.mark.parametrize(
    "value",
    [
        "",
        "***",
        encoded(
            {
                "v": 2,
                "started_at": "2026-07-22T12:00:00Z",
                "processing_run_id": "x",
            }
        ),
        encoded({"v": 1, "started_at": "invalid", "processing_run_id": "x"}),
        encoded(
            {
                "v": 1,
                "started_at": "2026-07-22T12:00:00",
                "processing_run_id": "x",
            }
        ),
        encoded({"v": 1, "started_at": "2026-07-22T12:00:00Z"}),
        encoded(
            {
                "v": 1,
                "started_at": "2026-07-22T12:00:00Z",
                "processing_run_id": "",
            }
        ),
        encoded(
            {
                "v": 1,
                "started_at": "2026-07-22T12:00:00Z",
                "processing_run_id": "x" * 129,
            }
        ),
        encoded(
            {
                "v": 1,
                "started_at": "2026-07-22T12:00:00Z",
                "processing_run_id": "x",
                "extra": True,
            }
        ),
        encoded({"v": 1, "started_at": 1, "processing_run_id": "x"}),
    ],
)
def test_invalid_processing_run_cursor_is_rejected(value: str) -> None:
    with pytest.raises(InvalidPaginationCursor):
        decode_processing_run_cursor(value)
