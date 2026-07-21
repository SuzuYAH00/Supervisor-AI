import pytest

from supervisor_ai.infrastructure.importing import JsonSyntaxError
from supervisor_ai.infrastructure.importing.parser import parse_json_text


def test_parses_valid_json() -> None:
    assert parse_json_text('{"event": {"id": "1"}}') == {
        "event": {"id": "1"}
    }


def test_rejects_invalid_json() -> None:
    with pytest.raises(JsonSyntaxError, match=r"\$: invalid JSON"):
        parse_json_text('{"event":')


@pytest.mark.parametrize("constant", ["NaN", "Infinity", "-Infinity", "1e999"])
def test_rejects_non_finite_numbers(constant: str) -> None:
    with pytest.raises(JsonSyntaxError, match="non-finite number"):
        parse_json_text(f'{{"value": {constant}}}')


def test_rejects_duplicate_keys() -> None:
    with pytest.raises(JsonSyntaxError, match="duplicate key 'id'"):
        parse_json_text('{"id": "first", "id": "second"}')
