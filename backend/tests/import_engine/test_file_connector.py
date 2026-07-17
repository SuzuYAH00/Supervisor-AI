import json
from datetime import UTC
from pathlib import Path
from unittest.mock import patch

import pytest

from supervisor_ai.import_engine import Connector, FileConnector, SourceReadError


def test_reads_valid_csv_without_inferring_types(tmp_path: Path) -> None:
    path = tmp_path / "records.csv"
    path.write_text("id,name,active\n1,Ana,true\n2,Beto,false\n", encoding="utf-8")

    result = FileConnector(path, source_name="test-source").read()

    assert [record.data for record in result.records] == [
        {"id": "1", "name": "Ana", "active": "true"},
        {"id": "2", "name": "Beto", "active": "false"},
    ]
    assert [record.metadata["line_number"] for record in result.records] == [2, 3]


def test_reads_empty_csv(tmp_path: Path) -> None:
    path = tmp_path / "empty.csv"
    path.write_text("", encoding="utf-8")

    result = FileConnector(path, source_name="test-source").read()

    assert result.records == []


def test_reads_csv_with_only_header_as_empty_result(tmp_path: Path) -> None:
    path = tmp_path / "header-only.csv"
    path.write_text("id,name\n", encoding="utf-8")

    result = FileConnector(path, source_name="test-source").read()

    assert result.records == []


@pytest.mark.parametrize("header", ["id,,name", "id,   ,name"])
def test_rejects_empty_csv_header(tmp_path: Path, header: str) -> None:
    path = tmp_path / "records.csv"
    path.write_text(f"{header}\n1,2,Ana\n", encoding="utf-8")

    with pytest.raises(SourceReadError, match="CSV headers are invalid"):
        FileConnector(path, source_name="test-source").read()


def test_rejects_duplicate_csv_header(tmp_path: Path) -> None:
    path = tmp_path / "records.csv"
    path.write_text("id,id\n1,2\n", encoding="utf-8")

    with pytest.raises(SourceReadError, match="CSV headers are invalid"):
        FileConnector(path, source_name="test-source").read()


def test_reads_valid_json_list_of_objects(tmp_path: Path) -> None:
    path = tmp_path / "records.json"
    payload = [
        {"id": 1, "active": True, "tags": ["new", None]},
        {"id": 2, "details": {"score": 9.5}},
    ]
    path.write_text(json.dumps(payload), encoding="utf-8")

    result = FileConnector(path, source_name="test-source").read()

    assert [record.data for record in result.records] == payload
    assert [record.metadata["record_index"] for record in result.records] == [0, 1]


def test_reads_empty_json_list(tmp_path: Path) -> None:
    path = tmp_path / "empty.json"
    path.write_text("[]", encoding="utf-8")

    result = FileConnector(path, source_name="test-source").read()

    assert result.records == []


def test_raises_sanitized_error_for_missing_file(tmp_path: Path) -> None:
    path = tmp_path / "secret-name.csv"

    with pytest.raises(SourceReadError, match="Source file does not exist") as caught:
        FileConnector(path, source_name="test-source").read()

    assert str(path) not in str(caught.value)
    assert caught.value.retryable is False


def test_raises_error_for_unsupported_extension(tmp_path: Path) -> None:
    path = tmp_path / "records.txt"
    path.write_text("content", encoding="utf-8")

    with pytest.raises(SourceReadError, match="extension is not supported"):
        FileConnector(path, source_name="test-source").read()


def test_raises_sanitized_error_for_invalid_csv(tmp_path: Path) -> None:
    path = tmp_path / "records.csv"
    invalid_content = 'id,notes\n1,"sensitive content'
    path.write_text(invalid_content, encoding="utf-8")

    with pytest.raises(SourceReadError, match="CSV file is invalid") as caught:
        FileConnector(path, source_name="test-source").read()

    assert invalid_content not in str(caught.value)


def test_raises_sanitized_error_for_invalid_json(tmp_path: Path) -> None:
    path = tmp_path / "records.json"
    invalid_content = '[{"token": "sensitive"}'
    path.write_text(invalid_content, encoding="utf-8")

    with pytest.raises(SourceReadError, match="JSON file is invalid") as caught:
        FileConnector(path, source_name="test-source").read()

    assert invalid_content not in str(caught.value)


def test_rejects_json_root_that_is_not_a_list(tmp_path: Path) -> None:
    path = tmp_path / "records.json"
    path.write_text('{"id": 1}', encoding="utf-8")

    with pytest.raises(SourceReadError, match="root must be a list of objects"):
        FileConnector(path, source_name="test-source").read()


def test_rejects_json_item_that_is_not_an_object(tmp_path: Path) -> None:
    path = tmp_path / "records.json"
    path.write_text('[{"id": 1}, 2]', encoding="utf-8")

    with pytest.raises(SourceReadError, match="items must be objects"):
        FileConnector(path, source_name="test-source").read()


def test_rejects_duplicate_json_keys_in_nested_object(tmp_path: Path) -> None:
    path = tmp_path / "records.json"
    path.write_text('[{"details": {"id": 1, "id": 2}}]', encoding="utf-8")

    with pytest.raises(SourceReadError, match="contains duplicate keys"):
        FileConnector(path, source_name="test-source").read()


def test_classifies_permission_error_as_not_retryable(tmp_path: Path) -> None:
    path = tmp_path / "records.json"
    path.write_text("[]", encoding="utf-8")

    with (
        patch.object(Path, "open", side_effect=PermissionError),
        pytest.raises(SourceReadError, match="Permission denied") as caught,
    ):
        FileConnector(path, source_name="test-source").read()

    assert caught.value.retryable is False


def test_populates_file_and_read_metadata(tmp_path: Path) -> None:
    path = tmp_path / "records.json"
    path.write_text('[{"id": 1}]', encoding="utf-8")

    result = FileConnector(path, source_name="logical-source").read()

    assert result.metadata.source_name == "logical-source"
    assert result.metadata.read_at.tzinfo is UTC
    assert result.metadata.attributes == {
        "file_name": "records.json",
        "file_extension": ".json",
        "format": "json",
        "size_bytes": path.stat().st_size,
    }
    assert result.records[0].metadata == {
        "file_name": "records.json",
        "record_index": 0,
    }


def test_implements_connector_structurally(tmp_path: Path) -> None:
    path = tmp_path / "records.json"
    path.write_text("[]", encoding="utf-8")

    connector = FileConnector(path, source_name="test-source")

    assert isinstance(connector, Connector)
