from collections.abc import Iterable

from supervisor_ai.processing_engine.processor import Processor
from supervisor_ai.processing_engine.types import (
    ProcessedRecord,
    ProcessingOutcome,
    RecordRejection,
)


class CompositeProcessor:
    """Executa uma sequência não vazia e ordenada de processors técnicos.

    A primeira etapa recebe o contexto importado. Cada etapa seguinte recebe o
    ``ProcessedRecord`` produzido pela anterior. Uma cadeia vazia é inválida,
    pois não há resultado processado legítimo que possa ser produzido.
    """

    def __init__(self, processors: Iterable[Processor]) -> None:
        self.processors = tuple(processors)
        if not self.processors:
            raise ValueError("Composite processor requires at least one processor.")

    def process(self, record: ProcessedRecord) -> ProcessingOutcome:
        """Executa as etapas até concluir, rejeitar ou propagar uma falha."""
        current = record

        for processor in self.processors:
            outcome = processor.process(current)
            if isinstance(outcome, RecordRejection):
                return outcome
            current = outcome

        return current
