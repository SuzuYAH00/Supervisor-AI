from datetime import UTC, datetime

from supervisor_ai.infrastructure.external.mk.database import MK_SOURCE_TIMEZONE


def mk_local_datetime_to_utc(value: datetime | None) -> datetime | None:
    """Interpreta o timestamp naive do MK em Fortaleza antes de convertê-lo."""
    if value is None:
        return None
    if value.tzinfo is not None or value.utcoffset() is not None:
        raise ValueError("MK source datetime must be naive")
    return value.replace(tzinfo=MK_SOURCE_TIMEZONE).astimezone(UTC)
