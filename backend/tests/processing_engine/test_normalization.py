from datetime import UTC, date, datetime
from decimal import Decimal
from typing import cast
from uuid import uuid4

from supervisor_ai.import_engine import RawRecord, RawValue, SourceMetadata
from supervisor_ai.processing_engine import (
    ImportedRecordContext,
    Processor,
    TechnicalNormalizationProcessor,
)
from supervisor_ai.processing_engine.types import ProcessedValue


def make_context(data: dict[str, ProcessedValue]) -> ImportedRecordContext:
    return ImportedRecordContext(
        raw_record=RawRecord(data=cast(dict[str, RawValue], data)),
        source_metadata=SourceMetadata(
            source_name="test-source",
            read_at=datetime(2026, 7, 17, tzinfo=UTC),
        ),
    )


def test_strips_external_spaces_from_strings() -> None:
    context = make_context({"name": "  Ana Silva  ", "clean": "value"})

    result = TechnicalNormalizationProcessor().process(context)

    assert result.data == {"name": "Ana Silva", "clean": "value"}


def test_normalizes_empty_strings_to_none() -> None:
    context = make_context({"empty": "", "spaces": "   \t\n"})

    result = TechnicalNormalizationProcessor().process(context)

    assert result.data == {"empty": None, "spaces": None}


def test_normalizes_nested_lists_and_dictionaries() -> None:
    context = make_context(
        {
            "items": [" first ", [" ", "third"]],
            "details": {
                "label": " value ",
                "nested": {"empty": ""},
            },
        }
    )

    result = TechnicalNormalizationProcessor().process(context)

    assert result.data == {
        "items": ["first", [None, "third"]],
        "details": {"label": "value", "nested": {"empty": None}},
    }


def test_preserves_numeric_values_without_conversion() -> None:
    decimal_value = Decimal("10.500")
    context = make_context(
        {
            "integer": 10,
            "float": 10.5,
            "decimal": decimal_value,
            "boolean": True,
        }
    )

    result = TechnicalNormalizationProcessor().process(context)

    assert result.data["integer"] == 10
    assert result.data["float"] == 10.5
    assert result.data["decimal"] is decimal_value
    assert result.data["boolean"] is True


def test_preserves_uuid_date_and_datetime_values() -> None:
    identifier = uuid4()
    date_value = date(2026, 7, 17)
    datetime_value = datetime(2026, 7, 17, 12, 30, tzinfo=UTC)
    context = make_context(
        {
            "identifier": identifier,
            "date": date_value,
            "datetime": datetime_value,
        }
    )

    result = TechnicalNormalizationProcessor().process(context)

    assert result.data["identifier"] is identifier
    assert result.data["date"] is date_value
    assert result.data["datetime"] is datetime_value


def test_preserves_origin_and_does_not_modify_raw_record() -> None:
    raw_data: dict[str, ProcessedValue] = {
        "name": "  Ana  ",
        "nested": [" value ", {"empty": " "}],
    }
    context = make_context(raw_data)

    result = TechnicalNormalizationProcessor().process(context)

    assert result.origin is context
    assert context.raw_record.data == raw_data
    assert context.raw_record.data["name"] == "  Ana  "


def test_processed_data_is_a_new_recursive_structure() -> None:
    context = make_context(
        {"items": ["value"], "details": {"label": "value"}}
    )

    result = TechnicalNormalizationProcessor().process(context)

    assert result.data is not context.raw_record.data
    assert result.data["items"] is not context.raw_record.data["items"]
    assert result.data["details"] is not context.raw_record.data["details"]


def test_implements_processor_structurally() -> None:
    assert isinstance(TechnicalNormalizationProcessor(), Processor)
