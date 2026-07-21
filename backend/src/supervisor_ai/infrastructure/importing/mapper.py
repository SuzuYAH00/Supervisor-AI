from datetime import UTC
from decimal import Decimal
from uuid import UUID

from supervisor_ai.application import CommercialEvent
from supervisor_ai.application.use_cases import (
    ProcessAndPersistCommercialEventCommand,
)
from supervisor_ai.infrastructure.importing.schema import (
    ValidatedEvidenceDocument,
    ValidatedImportDocument,
    parse_datetime,
)
from supervisor_ai.rules_engine import (
    ContractualEvidenceName,
    EvaluationContext,
    Evidence,
    EvidenceValue,
)


class JsonImportDocumentMapper:
    def map(
        self, document: ValidatedImportDocument
    ) -> ProcessAndPersistCommercialEventCommand:
        occurred_at = parse_datetime(
            document.event.occurred_at, "event.occurred_at"
        ).astimezone(UTC)
        received_at = parse_datetime(
            document.event.received_at, "event.received_at"
        ).astimezone(UTC)
        event = CommercialEvent(
            id=document.event.id,
            external_reference=document.event.external_reference,
            source=document.event.source,
            occurred_at=occurred_at,
            received_at=received_at,
            raw_payload=document.event.raw_payload,
            created_at=received_at,
        )
        evaluation = EvaluationContext(
            evaluation_id=UUID(document.evaluation.evaluation_id),
            subject_id=document.evaluation.subject_id,
            observed_at=parse_datetime(
                document.evaluation.observed_at, "evaluation.observed_at"
            ).astimezone(UTC),
            evidence=tuple(
                self._evidence(item) for item in document.evaluation.evidence
            ),
        )
        return ProcessAndPersistCommercialEventCommand(
            event=event,
            evaluation_context=evaluation,
            rules_engine_version=document.rules_engine_version,
        )

    @staticmethod
    def _evidence(document: ValidatedEvidenceDocument) -> Evidence:
        return Evidence(
            evidence_id=document.id,
            name=document.name,
            value=_map_evidence_value(document.name, document.value),
            observed_at=parse_datetime(
                document.observed_at, "evaluation.evidence.observed_at"
            ).astimezone(UTC),
        )


def _map_evidence_value(
    name: ContractualEvidenceName, value: object
) -> EvidenceValue:
    if name in {
        ContractualEvidenceName.PREVIOUS_ADDITIONALS,
        ContractualEvidenceName.CURRENT_ADDITIONALS,
    }:
        if not isinstance(value, list):
            raise TypeError("validated additional evidence must be an array")
        return tuple(value)
    if name in {
        ContractualEvidenceName.PREVIOUS_RECURRING_VALUE,
        ContractualEvidenceName.CURRENT_RECURRING_VALUE,
    }:
        if type(value) not in {int, float}:
            raise TypeError("validated monetary evidence must be numeric")
        return Decimal(str(value))
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value
    if isinstance(value, int):
        return value
    raise TypeError("validated evidence has no domain mapping")
