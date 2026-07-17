from typing import Protocol, runtime_checkable

from supervisor_ai.processing_engine.types import ProcessedRecord, ProcessingOutcome


@runtime_checkable
class Processor(Protocol):
    """Contrato estrutural para uma etapa técnica de processamento."""

    def process(self, record: ProcessedRecord) -> ProcessingOutcome:
        """Processa o registro em trânsito ou devolve sua rejeição esperada.

        Raises:
            ProcessingError: Quando uma falha técnica impedir o processamento.
        """
        ...
