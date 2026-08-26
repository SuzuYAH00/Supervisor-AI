from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from supervisor_ai.application.persistence import AttendanceFact
from supervisor_ai.rules_engine import RecurrenceAttendance, find_recurrences


class RecurrenceRegressionDifference(StrEnum):
    SOURCE_PRECISION = "source_precision"
    LEGACY_PROTOCOL_CORRUPTION = "legacy_protocol_corruption"
    LEGACY_DATE_ONLY = "legacy_date_only"
    OPERATOR_MAPPING = "operator_mapping"
    MISSING_MK_RECORD = "missing_mk_record"
    MISSING_LEGACY_RECORD = "missing_legacy_record"
    SEMANTIC_DIFFERENCE = "semantic_difference"
    PROJECTION_BUG = "projection_bug"
    UNRESOLVED = "unresolved"


@dataclass(frozen=True, slots=True)
class RecurrenceRegressionIssue:
    category: RecurrenceRegressionDifference
    legacy_fact_id: str | None
    mk_fact_id: str | None
    field: str


@dataclass(frozen=True, slots=True)
class RecurrenceRegressionResult:
    legacy_attendance_count: int
    mk_attendance_count: int
    legacy_recurrence_count: int
    mk_recurrence_count: int
    issues: tuple[RecurrenceRegressionIssue, ...]


def compare_recurrence_paths(
    legacy: tuple[AttendanceFact, ...],
    mk: tuple[AttendanceFact, ...],
    *,
    cohort_start: date,
    cohort_end: date,
    legacy_protocols: Mapping[str, str] | None = None,
    mk_protocols: Mapping[str, str] | None = None,
) -> RecurrenceRegressionResult:
    """Compara fontes sem misturá-las no cálculo oficial."""
    legacy_sorted = sorted(legacy, key=_semantic_order)
    mk_sorted = sorted(mk, key=_semantic_order)
    issues: list[RecurrenceRegressionIssue] = []
    for legacy_fact, mk_fact in zip(legacy_sorted, mk_sorted, strict=False):
        if legacy_fact.customer_code != mk_fact.customer_code:
            issues.append(_issue("customer_code", legacy_fact, mk_fact))
            continue
        if legacy_fact.occurred_at != mk_fact.occurred_at:
            category = (
                RecurrenceRegressionDifference.LEGACY_DATE_ONLY
                if legacy_fact.occurred_at.date() == mk_fact.occurred_at.date()
                else RecurrenceRegressionDifference.SOURCE_PRECISION
            )
            issues.append(
                RecurrenceRegressionIssue(
                    category, legacy_fact.id, mk_fact.id, "occurred_at"
                )
            )
        if legacy_fact.operator_id != mk_fact.operator_id:
            issues.append(
                RecurrenceRegressionIssue(
                    RecurrenceRegressionDifference.OPERATOR_MAPPING,
                    legacy_fact.id,
                    mk_fact.id,
                    "operator_id",
                )
            )
        for field in (
            "process",
            "opening_classification",
            "closing_classification",
        ):
            if getattr(legacy_fact, field) != getattr(mk_fact, field):
                issues.append(_issue(field, legacy_fact, mk_fact))
        if legacy_protocols is not None and mk_protocols is not None:
            legacy_protocol = legacy_protocols.get(legacy_fact.id)
            mk_protocol = mk_protocols.get(mk_fact.id)
            if legacy_protocol != mk_protocol:
                issues.append(
                    RecurrenceRegressionIssue(
                        RecurrenceRegressionDifference.LEGACY_PROTOCOL_CORRUPTION,
                        legacy_fact.id,
                        mk_fact.id,
                        "protocol",
                    )
                )
    if len(legacy_sorted) > len(mk_sorted):
        issues.extend(
            RecurrenceRegressionIssue(
                RecurrenceRegressionDifference.MISSING_MK_RECORD,
                item.id,
                None,
                "attendance",
            )
            for item in legacy_sorted[len(mk_sorted) :]
        )
    elif len(mk_sorted) > len(legacy_sorted):
        issues.extend(
            RecurrenceRegressionIssue(
                RecurrenceRegressionDifference.MISSING_LEGACY_RECORD,
                None,
                item.id,
                "attendance",
            )
            for item in mk_sorted[len(legacy_sorted) :]
        )

    legacy_recurrences = find_recurrences(
        tuple(_to_recurrence(item) for item in legacy),
        cohort_start=cohort_start,
        cohort_end=cohort_end,
    )
    mk_recurrences = find_recurrences(
        tuple(_to_recurrence(item) for item in mk),
        cohort_start=cohort_start,
        cohort_end=cohort_end,
    )
    return RecurrenceRegressionResult(
        len(legacy),
        len(mk),
        len(legacy_recurrences),
        len(mk_recurrences),
        tuple(issues),
    )


def _semantic_order(item: AttendanceFact) -> tuple[str, object, str]:
    return item.customer_code, item.occurred_at, item.id


def _issue(
    field: str, legacy: AttendanceFact, mk: AttendanceFact
) -> RecurrenceRegressionIssue:
    return RecurrenceRegressionIssue(
        RecurrenceRegressionDifference.SEMANTIC_DIFFERENCE,
        legacy.id,
        mk.id,
        field,
    )


def _to_recurrence(item: AttendanceFact) -> RecurrenceAttendance:
    return RecurrenceAttendance(
        attendance_id=item.id,
        customer_code=item.customer_code,
        operator_id=item.operator_id,
        channel=item.channel,
        occurred_at=item.occurred_at,
        process=item.process,
        opening_classification=item.opening_classification,
        closing_classification=item.closing_classification,
    )
