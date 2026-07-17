from typing import Protocol, runtime_checkable

from supervisor_ai.processing_engine.types import (
    ImportedRecordContext,
    ProcessingOutcome,
)


@runtime_checkable
class Processor(Protocol):
    """Contrato estrutural para preparação técnica de um registro bruto."""

    def process(self, context: ImportedRecordContext) -> ProcessingOutcome:
        """Processa um registro ou devolve sua rejeição esperada.

        Raises:
            ProcessingError: Quando uma falha técnica impedir o processamento.
        """
        ...
