from supervisor_ai.processing_engine.normalizers import TechnicalValueNormalizer
from supervisor_ai.processing_engine.types import (
    ImportedRecordContext,
    ProcessedRecord,
)


class TechnicalNormalizationProcessor:
    """Orquestra a normalização técnica genérica de um registro importado.

    A transformação recursiva pertence ao normalizador reutilizável. Este
    processor apenas preserva a origem e constrói o registro processado.
    """

    _normalizer = TechnicalValueNormalizer()

    def process(self, context: ImportedRecordContext) -> ProcessedRecord:
        """Produz uma nova estrutura normalizada sem modificar o registro bruto."""
        return ProcessedRecord(
            origin=context,
            data={
                key: self._normalizer.normalize(value)
                for key, value in context.raw_record.data.items()
            },
        )
