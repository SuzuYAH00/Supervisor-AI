import json
from copy import deepcopy


def document() -> dict[str, object]:
    return {
        "event": {
            "id": "event-json-1",
            "external_reference": "external-json-1",
            "source": "json-test",
            "occurred_at": "2026-07-21T10:00:00-03:00",
            "received_at": "2026-07-21T13:01:00Z",
            "raw_payload": {
                "contract_id": "contract-1",
                "nested": {"items": [1, True, None]},
            },
        },
        "evaluation": {
            "evaluation_id": "00000000-0000-0000-0000-000000000001",
            "subject_id": "contract-1",
            "observed_at": "2026-07-21T13:00:00Z",
            "evidence": [],
        },
        "rules_engine_version": "rules-json-1",
    }


def json_text(value: dict[str, object] | None = None) -> str:
    return json.dumps(deepcopy(value or document()))


def evidence(
    evidence_id: str,
    name: str,
    value: object,
    *,
    observed_at: str = "2026-07-21T13:00:00Z",
) -> dict[str, object]:
    return {
        "id": evidence_id,
        "name": name,
        "value": value,
        "observed_at": observed_at,
    }
