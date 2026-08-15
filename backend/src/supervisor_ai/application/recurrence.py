from dataclasses import dataclass
from datetime import date, timedelta

from supervisor_ai.rules_engine import RECURRENCE_WINDOW_DAYS

MAX_ATTENDANCE_ID_LENGTH = 128
MAX_ATTENDANCE_EXTERNAL_REFERENCE_LENGTH = 255
MAX_ATTENDANCE_SOURCE_LENGTH = 100
MAX_ATTENDANCE_CUSTOMER_CODE_LENGTH = 128
MAX_ATTENDANCE_OPERATOR_ID_LENGTH = 128
MAX_ATTENDANCE_CHANNEL_LENGTH = 100
MAX_CLASSIFICATION_CODE_LENGTH = 20
MAX_CLASSIFICATION_DESCRIPTION_LENGTH = 255


@dataclass(frozen=True, slots=True)
class AttendanceFilters:
    operator_id: str | None = None
    customer_code: str | None = None
    source: str | None = None
    channel: str | None = None
    start_date: date | None = None
    end_date: date | None = None

    def __post_init__(self) -> None:
        for value, name, maximum in (
            (self.operator_id, "operator_id", MAX_ATTENDANCE_OPERATOR_ID_LENGTH),
            (
                self.customer_code,
                "customer_code",
                MAX_ATTENDANCE_CUSTOMER_CODE_LENGTH,
            ),
            (self.source, "source", MAX_ATTENDANCE_SOURCE_LENGTH),
            (self.channel, "channel", MAX_ATTENDANCE_CHANNEL_LENGTH),
        ):
            if value is not None:
                _validate_text(value, name, maximum)
        if (
            self.start_date is not None
            and self.end_date is not None
            and self.start_date > self.end_date
        ):
            raise ValueError("start_date must not be after end_date")


@dataclass(frozen=True, slots=True)
class RecurrenceCohortQuery:
    reference_month: date
    observed_through: date
    operator_id: str | None = None
    source: str | None = None
    channel: str | None = None

    def __post_init__(self) -> None:
        if self.reference_month.day != 1:
            raise ValueError("reference_month must be the first day of a month")
        AttendanceFilters(
            operator_id=self.operator_id,
            source=self.source,
            channel=self.channel,
        )
        if self.observed_through < self.window_end:
            raise ValueError("the cohort observation window is incomplete")

    @property
    def cohort_end(self) -> date:
        if self.reference_month.month == 12:
            next_month = date(self.reference_month.year + 1, 1, 1)
        else:
            next_month = date(
                self.reference_month.year, self.reference_month.month + 1, 1
            )
        return next_month - timedelta(days=1)

    @property
    def window_end(self) -> date:
        return self.cohort_end + timedelta(days=RECURRENCE_WINDOW_DAYS)


def _validate_text(value: str, name: str, maximum: int) -> None:
    if not value.strip():
        raise ValueError(f"{name} must not be blank")
    if len(value) > maximum:
        raise ValueError(f"{name} must not exceed {maximum} characters")
