from __future__ import annotations

from io import BytesIO
import json
import struct
from pathlib import Path
from typing import Any


def load_schema(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def encode_record(record: dict[str, Any], schema: dict[str, Any]) -> bytes:
    try:
        from fastavro import schemaless_writer
    except ModuleNotFoundError:
        return _encode_record_fallback(record, schema)

    buffer = BytesIO()
    schemaless_writer(buffer, schema, record)
    return buffer.getvalue()


def decode_record(payload: bytes, schema: dict[str, Any]) -> dict[str, Any]:
    return _decode_record_fallback(payload, schema)


def _encode_record_fallback(record: dict[str, Any], schema: dict[str, Any]) -> bytes:
    buffer = BytesIO()
    for field in schema["fields"]:
        _write_value(buffer, record[field["name"]], _type_name(field["type"]))
    return buffer.getvalue()


def _decode_record_fallback(payload: bytes, schema: dict[str, Any]) -> dict[str, Any]:
    buffer = BytesIO(payload)
    result: dict[str, Any] = {}
    for field in schema["fields"]:
        result[field["name"]] = _read_value(buffer, _type_name(field["type"]))
    remaining = buffer.read()
    if remaining:
        raise ValueError("Unexpected trailing bytes in Avro payload")
    return result


def _type_name(avro_type: Any) -> str:
    if isinstance(avro_type, dict):
        return avro_type["type"]
    return avro_type


def _write_value(buffer: BytesIO, value: Any, avro_type: str) -> None:
    if avro_type == "string":
        encoded = value.encode("utf-8")
        _write_long(buffer, len(encoded))
        buffer.write(encoded)
        return
    if avro_type == "long":
        _write_long(buffer, int(value))
        return
    if avro_type == "double":
        buffer.write(struct.pack("<d", float(value)))
        return
    if avro_type == "boolean":
        buffer.write(b"\x01" if value else b"\x00")
        return
    raise ValueError(f"Unsupported Avro type: {avro_type}")


def _read_value(buffer: BytesIO, avro_type: str) -> Any:
    if avro_type == "string":
        length = _read_long(buffer)
        return buffer.read(length).decode("utf-8")
    if avro_type == "long":
        return _read_long(buffer)
    if avro_type == "double":
        return struct.unpack("<d", _read_exact(buffer, 8))[0]
    if avro_type == "boolean":
        return _read_exact(buffer, 1) == b"\x01"
    raise ValueError(f"Unsupported Avro type: {avro_type}")


def _write_long(buffer: BytesIO, value: int) -> None:
    encoded = (value << 1) ^ (value >> 63)
    while encoded & ~0x7F:
        buffer.write(bytes([(encoded & 0x7F) | 0x80]))
        encoded >>= 7
    buffer.write(bytes([encoded]))


def _read_long(buffer: BytesIO) -> int:
    shift = 0
    result = 0
    while True:
        byte = _read_exact(buffer, 1)[0]
        result |= (byte & 0x7F) << shift
        if not byte & 0x80:
            break
        shift += 7
    return (result >> 1) ^ -(result & 1)


def _read_exact(buffer: BytesIO, size: int) -> bytes:
    value = buffer.read(size)
    if len(value) != size:
        raise ValueError("Unexpected end of Avro payload")
    return value
