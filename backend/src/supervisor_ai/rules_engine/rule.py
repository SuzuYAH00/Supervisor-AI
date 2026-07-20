from typing import Protocol, runtime_checkable

from supervisor_ai.rules_engine.types import (
    EvaluationConclusion,
    EvaluationContext,
    RulePhase,
)


@runtime_checkable
class Rule(Protocol):
    """Contrato estrutural para uma regra pequena e sem efeitos externos."""

    @property
    def rule_id(self) -> str:
        """Identificador estável usado para auditoria da conclusão."""
        ...

    @property
    def phase(self) -> RulePhase:
        """Fase lógica da regra, sem definir sua ordem global de execução."""
        ...

    def evaluate(
        self,
        context: EvaluationContext,
        available_conclusions: tuple[EvaluationConclusion, ...],
    ) -> tuple[EvaluationConclusion, ...]:
        """Produz conclusões sem alterar o contexto ou executar efeitos."""
        ...
