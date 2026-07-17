from supervisor_ai.import_engine.types import ReadResult
from supervisor_ai.processing_engine.types import ImportedRecordContext


def build_processing_contexts(
    read_result: ReadResult,
) -> list[ImportedRecordContext]:
    """Constrói contextos preservando as referências e a ordem da importação."""
    return [
        ImportedRecordContext(
            raw_record=raw_record,
            source_metadata=read_result.metadata,
        )
        for raw_record in read_result.records
    ]
