from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

type EvidenceScalar = (
    str | bool | int | float | Decimal | date | datetime | UUID | None
)
type EvidenceValue = EvidenceScalar | tuple[EvidenceValue, ...]


class ConclusionStatus(StrEnum):
    """Condição explícita de uma proposição ou conclusão avaliada."""

    TRUE = "true"
    FALSE = "false"
    INDETERMINATE = "indeterminate"
    NOT_EVALUABLE = "not_evaluable"
    INCONSISTENT = "inconsistent"
    PENDING_HUMAN_REVIEW = "pending_human_review"


class ConclusionKind(StrEnum):
    """Natureza arquitetural de uma conclusão produzida pelo motor."""

    DERIVED_FACT = "derived_fact"
    DOMAIN_DECISION = "domain_decision"
    INDICATED_EFFECT = "indicated_effect"


class RulePhase(StrEnum):
    """Fase lógica de uma regra, sem impor uma cadeia global rígida."""

    CONTRACTUAL_FACTS = "contractual_facts"
    COMMERCIAL_CLASSIFICATION = "commercial_classification"
    AUTHORSHIP_AND_ELIGIBILITY = "authorship_and_eligibility"
    FINANCIAL_VALIDATION = "financial_validation"
    MONITORING_AND_PENALTIES = "monitoring_and_penalties"


@dataclass(frozen=True, slots=True)
class Evidence:
    """Evidência observada e imutável usada durante uma avaliação.

    ``source_reference`` preserva uma referência auditável sem acoplar o
    contrato a fornecedores, banco de dados ou formatos técnicos de origem.
    Coleções em ``value`` usam tuplas para evitar mutação acidental.
    """

    evidence_id: str
    name: str
    value: EvidenceValue
    observed_at: datetime
    source_reference: str | None = None


@dataclass(frozen=True, slots=True)
class EvaluationContext:
    """Snapshot consistente de evidências de entrada para uma avaliação.

    O contexto não contém decisões, não busca dados e não é modificado pelas
    regras. Uma mudança nas evidências exige um novo contexto de avaliação.
    """

    evaluation_id: UUID
    subject_id: str
    observed_at: datetime
    evidence: tuple[Evidence, ...]


@dataclass(frozen=True, slots=True)
class Justification:
    """Explicação auditável da origem de uma conclusão.

    As referências são identificadores, não objetos de infraestrutura. Isso
    preserva causalidade sem fazer uma regra conhecer persistência ou serviços.
    """

    rule_id: str
    summary: str
    evidence_ids: tuple[str, ...] = ()
    supporting_conclusion_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class EvaluationConclusion:
    """Proposição derivada, decisão de domínio ou efeito apenas indicado."""

    conclusion_id: str
    name: str
    kind: ConclusionKind
    status: ConclusionStatus
    justification: Justification
    value: EvidenceValue = None


@dataclass(frozen=True, slots=True)
class CandidateDomainEvent:
    """Evento de domínio candidato fundamentado pela avaliação.

    O contrato não declara que o evento foi publicado, persistido ou que um
    efeito posterior foi materializado.
    """

    name: str
    subject_id: str
    supporting_conclusion_ids: tuple[str, ...]
    justification: Justification


@dataclass(frozen=True, slots=True)
class EvaluationResult:
    """Resultado imutável, auditável e livre de efeitos de uma avaliação."""

    evaluation_id: UUID
    conclusions: tuple[EvaluationConclusion, ...] = ()
    evidence: tuple[Evidence, ...] = ()
    missing_information: tuple[str, ...] = ()
    inconsistencies: tuple[str, ...] = ()
    manual_review_reasons: tuple[str, ...] = ()
    candidate_domain_events: tuple[CandidateDomainEvent, ...] = ()
