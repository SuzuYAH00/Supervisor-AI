import json
import math

from supervisor_ai.infrastructure.importing.errors import JsonSyntaxError


def parse_json_text(text: str) -> object:
    try:
        return json.loads(
            text,
            object_pairs_hook=_object_without_duplicate_keys,
            parse_constant=_reject_non_standard_number,
            parse_float=_parse_finite_float,
        )
    except JsonSyntaxError:
        raise
    except (json.JSONDecodeError, TypeError) as error:
        raise JsonSyntaxError(
            f"$: invalid JSON at line {error.lineno}, column {error.colno}"
            if isinstance(error, json.JSONDecodeError)
            else "$: input must be JSON text"
        ) from error


def _object_without_duplicate_keys(
    pairs: list[tuple[str, object]],
) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise JsonSyntaxError(f"$: duplicate key {key!r}")
        result[key] = value
    return result


def _reject_non_standard_number(value: str) -> object:
    raise JsonSyntaxError(f"$: non-finite number {value!r} is not valid JSON")


def _parse_finite_float(value: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed):
        raise JsonSyntaxError(f"$: non-finite number {value!r} is not valid JSON")
    return parsed
