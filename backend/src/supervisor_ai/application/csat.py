from dataclasses import dataclass
from datetime import date

MAX_CSAT_ID_LENGTH = 128
MAX_CSAT_EXTERNAL_REFERENCE_LENGTH = 255
MAX_CSAT_SOURCE_LENGTH = 100
MAX_CSAT_COLLABORATOR_ID_LENGTH = 128
MAX_CSAT_CHANNEL_LENGTH = 100


@dataclass(frozen=True, slots=True)
class CsatFilters:
    collaborator_id: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    source: str | None = None
    channel: str | None = None

    def __post_init__(self) -> None:
        _validate_optional_text(
            self.collaborator_id,
            "collaborator_id",
            MAX_CSAT_COLLABORATOR_ID_LENGTH,
        )
        _validate_optional_text(self.source, "source", MAX_CSAT_SOURCE_LENGTH)
        _validate_optional_text(self.channel, "channel", MAX_CSAT_CHANNEL_LENGTH)
        if (
            self.start_date is not None
            and self.end_date is not None
            and self.start_date > self.end_date
        ):
            raise ValueError("start_date must not be after end_date")


def _validate_optional_text(
    value: str | None, field_name: str, maximum_length: int
) -> None:
    if value is None:
        return
    if not value.strip():
        raise ValueError(f"{field_name} must not be blank")
    if len(value) > maximum_length:
        raise ValueError(f"{field_name} must not exceed {maximum_length} characters")
