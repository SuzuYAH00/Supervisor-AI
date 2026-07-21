from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from supervisor_ai.rules_engine.remuneration_amount import (
    Currency,
    RemunerationAmountResult,
    RemunerationAmountStatus,
)

LEDGER_ENTRY_ID_PREFIX = "ledger.remuneration.credit:"


class LedgerEntryType(StrEnum):
    """Tipos reconhecidos pelo ledger; a Fase F2 cria somente crédito."""

    CREDIT = "credit"
    DEBIT = "debit"
    ADJUSTMENT = "adjustment"


class LedgerPostingStatus(StrEnum):
    """Estados da decisão pura de postagem."""

    POSTED = "posted"
    ALREADY_POSTED = "already_posted"
    NOT_APPLICABLE = "not_applicable"
    PENDING_MANUAL_REVIEW = "pending_manual_review"
    NOT_EVALUABLE = "not_evaluable"


class LedgerPostingReason(StrEnum):
    """Motivos estáveis do resultado de postagem."""

    REMUNERATION_CALCULATED = "remuneration_calculated"
    REMUNERATION_NOT_CALCULATED = "remuneration_not_calculated"
    SOURCE_PENDING_MANUAL_REVIEW = "source_pending_manual_review"
    SOURCE_NOT_EVALUABLE = "source_not_evaluable"
    EVENT_ALREADY_POSTED = "event_already_posted"
    DUPLICATE_EVENT_CREDIT = "duplicate_event_credit"
    MISSING_BENEFICIARY = "missing_beneficiary"
    MISSING_POSTED_AT = "missing_posted_at"
    MISSING_SOURCE_REFERENCE = "missing_source_reference"
    INVALID_AMOUNT = "invalid_amount"
    INCONSISTENT_INPUT = "inconsistent_input"
    LEDGER_REFERENCE_CONFLICT = "ledger_reference_conflict"


@dataclass(frozen=True, slots=True)
class ExistingLedgerEntryReference:
    """Histórico mínimo para idempotência, sem carregar persistência."""

    entry_id: str
    event_id: str
    beneficiary_id: str
    entry_type: LedgerEntryType
    amount: Decimal
    currency: Currency
    posting_reference: str
    source_reference_ids: tuple[str, ...]
    remuneration_calculation_reference: str
    invoice_id: str | None = None


@dataclass(frozen=True, slots=True)
class LedgerEntry:
    """Fato financeiro imutável; saldo não pertence ao lançamento."""

    entry_id: str
    event_id: str
    beneficiary_id: str
    entry_type: LedgerEntryType
    amount: Decimal
    currency: Currency
    posted_at: datetime
    posting_reference: str
    source_reference_ids: tuple[str, ...]
    remuneration_calculation_reference: str
    invoice_id: str | None = None


@dataclass(frozen=True, slots=True)
class LedgerPostingInput:
    """Entrada completa da decisão de postagem, incluindo histórico mínimo."""

    event_id: str
    beneficiary_id: str | None
    remuneration_amount_result: RemunerationAmountResult
    posted_at: datetime | None
    posting_reference: str | None
    source_reference_ids: tuple[str, ...]
    remuneration_calculation_reference: str | None
    invoice_id: str | None = None
    existing_entries: tuple[ExistingLedgerEntryReference, ...] = ()
    has_ledger_reference_conflict: bool = False
    has_inconsistent_input: bool = False


@dataclass(frozen=True, slots=True)
class LedgerPostingResult:
    """Resultado da decisão; não significa que houve persistência."""

    status: LedgerPostingStatus
    reasons: tuple[LedgerPostingReason, ...]
    entry: LedgerEntry | None
    event_id: str
    beneficiary_id: str | None
    matching_existing_entry_id: str | None
    source_reference_ids: tuple[str, ...]


def build_credit_entry_id(event_id: str) -> str:
    """Produz identidade estável de um único crédito por evento."""

    return f"{LEDGER_ENTRY_ID_PREFIX}{event_id}"


class RemunerationLedgerPostingEvaluator:
    """Produz crédito imutável sem persistir nem recalcular remuneração."""

    def evaluate(self, data: LedgerPostingInput) -> LedgerPostingResult:
        source_ids = tuple(sorted(data.source_reference_ids))
        if self._is_structurally_inconsistent(data):
            return self._result(
                data,
                LedgerPostingStatus.NOT_EVALUABLE,
                (LedgerPostingReason.INCONSISTENT_INPUT,),
                source_ids,
            )

        source_status = data.remuneration_amount_result.status
        if source_status is RemunerationAmountStatus.NOT_EVALUABLE:
            return self._result(
                data,
                LedgerPostingStatus.NOT_EVALUABLE,
                (LedgerPostingReason.SOURCE_NOT_EVALUABLE,),
                source_ids,
            )
        if source_status is RemunerationAmountStatus.PENDING_MANUAL_REVIEW:
            return self._result(
                data,
                LedgerPostingStatus.PENDING_MANUAL_REVIEW,
                (LedgerPostingReason.SOURCE_PENDING_MANUAL_REVIEW,),
                source_ids,
            )
        if source_status is RemunerationAmountStatus.NOT_APPLICABLE:
            return self._result(
                data,
                LedgerPostingStatus.NOT_APPLICABLE,
                (LedgerPostingReason.REMUNERATION_NOT_CALCULATED,),
                source_ids,
            )

        missing_reason = self._missing_reason(data)
        if missing_reason is not None:
            return self._result(
                data,
                LedgerPostingStatus.NOT_EVALUABLE,
                (missing_reason,),
                source_ids,
            )
        if not self._has_valid_amount(data.remuneration_amount_result):
            return self._result(
                data,
                LedgerPostingStatus.NOT_EVALUABLE,
                (LedgerPostingReason.INVALID_AMOUNT,),
                source_ids,
            )
        if data.has_ledger_reference_conflict:
            return self._result(
                data,
                LedgerPostingStatus.PENDING_MANUAL_REVIEW,
                (LedgerPostingReason.LEDGER_REFERENCE_CONFLICT,),
                source_ids,
            )

        matching = tuple(
            entry
            for entry in data.existing_entries
            if entry.entry_type is LedgerEntryType.CREDIT
            and entry.event_id == data.event_id
        )
        if len(matching) > 1:
            return self._result(
                data,
                LedgerPostingStatus.PENDING_MANUAL_REVIEW,
                (LedgerPostingReason.DUPLICATE_EVENT_CREDIT,),
                source_ids,
            )
        if matching:
            existing = matching[0]
            if self._is_compatible(existing, data, source_ids):
                return self._result(
                    data,
                    LedgerPostingStatus.ALREADY_POSTED,
                    (LedgerPostingReason.EVENT_ALREADY_POSTED,),
                    source_ids,
                    matching_existing_entry_id=existing.entry_id,
                )
            return self._result(
                data,
                LedgerPostingStatus.PENDING_MANUAL_REVIEW,
                (LedgerPostingReason.LEDGER_REFERENCE_CONFLICT,),
                source_ids,
                matching_existing_entry_id=existing.entry_id,
            )

        entry = LedgerEntry(
            entry_id=build_credit_entry_id(data.event_id),
            event_id=data.remuneration_amount_result.event_id,
            beneficiary_id=data.beneficiary_id,
            entry_type=LedgerEntryType.CREDIT,
            amount=data.remuneration_amount_result.remuneration_amount,
            currency=data.remuneration_amount_result.currency,
            posted_at=data.posted_at,
            posting_reference=data.posting_reference,
            source_reference_ids=source_ids,
            remuneration_calculation_reference=(
                data.remuneration_calculation_reference
            ),
            invoice_id=data.invoice_id,
        )
        return self._result(
            data,
            LedgerPostingStatus.POSTED,
            (LedgerPostingReason.REMUNERATION_CALCULATED,),
            source_ids,
            entry=entry,
        )

    @staticmethod
    def _result(
        data: LedgerPostingInput,
        status: LedgerPostingStatus,
        reasons: tuple[LedgerPostingReason, ...],
        source_ids: tuple[str, ...],
        *,
        entry: LedgerEntry | None = None,
        matching_existing_entry_id: str | None = None,
    ) -> LedgerPostingResult:
        return LedgerPostingResult(
            status=status,
            reasons=reasons,
            entry=entry,
            event_id=data.event_id,
            beneficiary_id=data.beneficiary_id,
            matching_existing_entry_id=matching_existing_entry_id,
            source_reference_ids=source_ids,
        )

    @staticmethod
    def _missing_reason(data: LedgerPostingInput) -> LedgerPostingReason | None:
        if not data.beneficiary_id:
            return LedgerPostingReason.MISSING_BENEFICIARY
        if data.posted_at is None:
            return LedgerPostingReason.MISSING_POSTED_AT
        if not data.posting_reference or not data.remuneration_calculation_reference:
            return LedgerPostingReason.MISSING_SOURCE_REFERENCE
        if not data.source_reference_ids:
            return LedgerPostingReason.MISSING_SOURCE_REFERENCE
        return None

    @staticmethod
    def _has_valid_amount(result: RemunerationAmountResult) -> bool:
        amount = result.remuneration_amount
        return (
            isinstance(amount, Decimal)
            and amount.is_finite()
            and amount > Decimal("0")
            and isinstance(result.currency, Currency)
        )

    @staticmethod
    def _is_compatible(
        existing: ExistingLedgerEntryReference,
        data: LedgerPostingInput,
        source_ids: tuple[str, ...],
    ) -> bool:
        result = data.remuneration_amount_result
        return all(
            (
                existing.beneficiary_id == data.beneficiary_id,
                existing.amount == result.remuneration_amount,
                existing.currency is result.currency,
                existing.posting_reference == data.posting_reference,
                tuple(sorted(existing.source_reference_ids)) == source_ids,
                existing.remuneration_calculation_reference
                == data.remuneration_calculation_reference,
                existing.invoice_id == data.invoice_id,
            )
        )

    @staticmethod
    def _is_structurally_inconsistent(data: LedgerPostingInput) -> bool:
        result = data.remuneration_amount_result
        entry_ids = tuple(entry.entry_id for entry in data.existing_entries)
        return any(
            (
                data.has_inconsistent_input,
                not data.event_id,
                result.event_id != data.event_id,
                len(entry_ids) != len(set(entry_ids)),
                data.posted_at is not None and not _is_aware(data.posted_at),
                any(
                    not _is_valid_existing_reference(entry)
                    for entry in data.existing_entries
                ),
            )
        )


def _is_valid_existing_reference(entry: ExistingLedgerEntryReference) -> bool:
    if not isinstance(entry.amount, Decimal):
        return False
    return (
        bool(entry.entry_id)
        and bool(entry.event_id)
        and bool(entry.beneficiary_id)
        and isinstance(entry.entry_type, LedgerEntryType)
        and entry.amount.is_finite()
        and entry.amount > Decimal("0")
        and isinstance(entry.currency, Currency)
        and bool(entry.posting_reference)
        and bool(entry.remuneration_calculation_reference)
    )


def _is_aware(value: datetime) -> bool:
    return value.tzinfo is not None and value.utcoffset() is not None
