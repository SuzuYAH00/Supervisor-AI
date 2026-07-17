from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from supervisor_ai.import_engine.types import RawRecord, RawValue, SourceMetadata

type ProcessedScalar = (
    str | bool | int | float | Decimal | date | datetime | UUID | None
)
type ProcessedValue = (
    ProcessedScalar | list[ProcessedValue] | dict[str, ProcessedValue]
)


@dataclass(slots=True)
class ImportedRecordContext:
    """Registro importado e sua identidade técnica no fluxo atual.

    ``trace_id`` correlaciona a entrada somente durante o fluxo atual e não
    representa uma identidade persistente definitiva.
    """

    raw_record: RawRecord
    source_metadata: SourceMetadata
    trace_id: UUID = field(default_factory=uuid4)


@dataclass(slots=True)
class ProcessedRecord:
    """Registro preparado genericamente, ainda sem regras de negócio.

    ``origin`` preserva a linhagem em memória nesta execução. Auditoria
    histórica imutável dependerá da persistência implementada futuramente.
    """

    origin: ImportedRecordContext
    data: dict[str, ProcessedValue]
    metadata: dict[str, RawValue] = field(default_factory=dict)


@dataclass(slots=True)
class RecordRejection:
    """Rejeição esperada que preserva a linhagem em memória da execução.

    Auditoria histórica imutável dependerá da persistência implementada
    futuramente.
    """

    origin: ImportedRecordContext
    reason_code: str
    message: str
    metadata: dict[str, RawValue] = field(default_factory=dict)


type ProcessingOutcome = ProcessedRecord | RecordRejection


@dataclass(slots=True)
class BatchProcessingResult:
    """Resultados válidos e rejeições esperadas de um lote processado."""

    processed: list[ProcessedRecord] = field(default_factory=list)
    rejected: list[RecordRejection] = field(default_factory=list)


class ProcessingError(Exception):
    """Falha técnica que impede a continuidade do processamento do lote."""
