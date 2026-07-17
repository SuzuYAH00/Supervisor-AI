from collections.abc import Iterable

from supervisor_ai.processing_engine.processor import Processor
from supervisor_ai.processing_engine.types import (
    BatchProcessingResult,
    ImportedRecordContext,
    ProcessedRecord,
    ProcessingError,
    RecordRejection,
)


def process_batch(
    processor: Processor,
    contexts: Iterable[ImportedRecordContext],
) -> BatchProcessingResult:
    """Processa sequencialmente um lote e separa resultados de rejeições.

    Falhas técnicas interrompem imediatamente a execução e nenhum resultado
    parcial é devolvido. Rejeições esperadas não interrompem o lote. A ordem é
    preservada separadamente em ``processed`` e ``rejected``; não existe uma
    ordem global combinada entre as duas coleções.
    """
    result = BatchProcessingResult()

    for context in contexts:
        outcome = processor.process(context)
        if isinstance(outcome, ProcessedRecord):
            result.processed.append(outcome)
        elif isinstance(outcome, RecordRejection):
            result.rejected.append(outcome)
        else:
            raise ProcessingError("Processor returned an unsupported outcome.")

    return result
