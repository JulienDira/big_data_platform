from __future__ import annotations

from io import BytesIO
import json
from pathlib import Path
from typing import Any

from fastavro import parse_schema, schemaless_reader, schemaless_writer


def load_schema(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def encode_record(record: dict[str, Any], schema: dict[str, Any]) -> bytes:
    buffer = BytesIO()
    schemaless_writer(buffer, parse_schema(schema), record)
    return buffer.getvalue()


def decode_record(payload: bytes, schema: dict[str, Any]) -> dict[str, Any]:
    buffer = BytesIO(payload)
    try:
        result = schemaless_reader(buffer, parse_schema(schema))
    except Exception as exc:
        raise ValueError("Invalid Avro payload") from exc

    remaining = buffer.read()
    if remaining:
        raise ValueError("Invalid Avro payload: trailing bytes")
    return dict(result)
