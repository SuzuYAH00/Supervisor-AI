from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

from supervisor_ai.import_engine import RawRecord, SourceMetadata
from supervisor_ai.processing_engine import (
    ImportedRecordContext,
    ProcessedRecord,
    Processor,
    TechnicalNormalizationProcessor,
)


def make_record(data: dict) -> ProcessedRecord:
    context = ImportedRecordContext(
        raw_record=RawRecord(data={"must_not_be_read": " raw "}),
        source_metadata=SourceMetadata(
            source_name="test-source",
            read_at=datetime(2026, 7, 17, tzinfo=UTC),
        ),
    )
    return ProcessedRecord(origin=context, data=data)


def test_normalizes_strings_and_empty_values() -> None:
    record = make_record(
        {"name": "  Ana Silva  ", "clean": "value", "empty": "  "}
    )

    result = TechnicalNormalizationProcessor().process(record)

    assert result.data == {"name": "Ana Silva", "clean": "value", "empty": None}


def test_normalizes_nested_lists_and_dictionaries() -> None:
    record = make_record(
        {
            "items": [" first ", [" ", "third"]],
            "details": {"label": " value ", "nested": {"empty": ""}},
        }
    )

    result = TechnicalNormalizationProcessor().process(record)

    assert result.data == {
        "items": ["first", [None, "third"]],
        "details": {"label": "value", "nested": {"empty": None}},
    }


def test_preserves_supported_scalar_values() -> None:
    decimal_value = Decimal("10.500")
    identifier = uuid4()
    date_value = date(2026, 7, 17)
    datetime_value = datetime(2026, 7, 17, 12, 30, tzinfo=UTC)
    record = make_record(
        {
            "integer": 10,
            "float": 10.5,
            "decimal": decimal_value,
            "boolean": True,
            "identifier": identifier,
            "date": date_value,
            "datetime": datetime_value,
        }
    )

    result = TechnicalNormalizationProcessor().process(record)

    assert result.data["integer"] == 10
    assert result.data["float"] == 10.5
    assert result.data["decimal"] is decimal_value
    assert result.data["boolean"] is True
    assert result.data["identifier"] is identifier
    assert result.data["date"] is date_value
    assert result.data["datetime"] is datetime_value


def test_preserves_origin_and_does_not_modify_received_record() -> None:
    data = {"name": "  Ana  ", "nested": [" value ", {"empty": " "}]}
    record = make_record(data)

    result = TechnicalNormalizationProcessor().process(record)

    assert result.origin is record.origin
    assert record.data == data
    assert record.data["name"] == "  Ana  "
    assert result.data is not record.data
    assert result.data["nested"] is not record.data["nested"]
    assert "must_not_be_read" not in result.data


def test_implements_processor_structurally() -> None:
    assert isinstance(TechnicalNormalizationProcessor(), Processor)
