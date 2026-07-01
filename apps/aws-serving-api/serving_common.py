from __future__ import annotations

import base64
import json
import re
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any


DEFAULT_SYMBOLS = ("BTCUSDC", "ETHUSDC", "SOLUSDC")
DEFAULT_INTERVALS = ("1s", "1m", "15m", "1h")

NUMERIC_FIELDS = {
    "open",
    "high",
    "low",
    "close",
    "volume",
    "ema_12",
    "ema_26",
    "macd",
    "rsi_14",
    "bollinger_middle",
    "bollinger_upper",
    "bollinger_lower",
    "open_price",
    "close_price",
    "high_price",
    "low_price",
    "daily_volume",
    "avg_rsi_14",
    "avg_macd",
    "volatility_score",
}

INTEGER_FIELDS = {
    "number_of_trades",
    "signal_score",
    "expires_at_epoch",
}

TIMESTAMP_FIELDS = {
    "open_time",
    "close_time",
    "updated_at",
    "loaded_at",
    "generated_at",
}

DATE_FIELDS = {"event_date"}

TOKEN_RE = re.compile(r"^[A-Za-z0-9_-]+={0,2}$")


class ApiError(Exception):
    status_code = 400

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class BadRequest(ApiError):
    status_code = 400


class NotFound(ApiError):
    status_code = 404


class ServiceFailure(ApiError):
    status_code = 502


class ServiceTimeout(ApiError):
    status_code = 504


def csv_values(value: str | None, default: tuple[str, ...]) -> tuple[str, ...]:
    if not value:
        return default
    parsed = tuple(item.strip() for item in value.split(",") if item.strip())
    return parsed or default


def require_allowed(value: str | None, name: str, allowed: tuple[str, ...]) -> str:
    if not value:
        raise BadRequest(f"Missing required parameter: {name}")
    if value not in allowed:
        raise BadRequest(f"Invalid {name}: {value}")
    return value


def bounded_limit(raw_value: str | None, *, default: int, maximum: int) -> int:
    if raw_value is None or raw_value == "":
        return default
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise BadRequest("limit must be an integer") from exc
    if value < 1:
        raise BadRequest("limit must be greater than zero")
    if value > maximum:
        raise BadRequest(f"limit must be less than or equal to {maximum}")
    return value


def parse_timestamp_filter(value: str | None, name: str) -> str | None:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        if "T" in normalized or " " in normalized:
            parsed = datetime.fromisoformat(normalized)
            if parsed.tzinfo is not None:
                parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
            return parsed.strftime("%Y-%m-%d %H:%M:%S")
        parsed_date = date.fromisoformat(normalized)
        return f"{parsed_date.isoformat()} 00:00:00"
    except ValueError as exc:
        raise BadRequest(f"{name} must be an ISO date or timestamp") from exc


def parse_date_filter(value: str | None, name: str) -> str | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError as exc:
        raise BadRequest(f"{name} must be an ISO date") from exc


def sql_string(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def encode_next_token(query_execution_id: str, token: str | None) -> str | None:
    if not token:
        return None
    payload = json.dumps(
        {"query_execution_id": query_execution_id, "token": token},
        separators=(",", ":"),
    ).encode("utf-8")
    return base64.urlsafe_b64encode(payload).decode("ascii")


def decode_next_token(value: str | None) -> dict[str, str] | None:
    if not value:
        return None
    if len(value) > 4096 or not TOKEN_RE.match(value):
        raise BadRequest("Invalid next_token")
    try:
        decoded = base64.urlsafe_b64decode(value.encode("ascii"))
        payload = json.loads(decoded.decode("utf-8"))
    except (ValueError, json.JSONDecodeError) as exc:
        raise BadRequest("Invalid next_token") from exc

    query_execution_id = payload.get("query_execution_id")
    token = payload.get("token")
    if not query_execution_id or not token:
        raise BadRequest("Invalid next_token")
    return {"query_execution_id": query_execution_id, "token": token}


def to_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise BadRequest(f"Invalid numeric value: {value}") from exc


def to_dynamodb_attribute(value: Any) -> dict[str, Any]:
    if value is None:
        return {"NULL": True}
    if isinstance(value, bool):
        return {"BOOL": value}
    if isinstance(value, int):
        return {"N": str(value)}
    if isinstance(value, float):
        return {"N": str(Decimal(str(value)))}
    if isinstance(value, Decimal):
        return {"N": str(value)}
    if isinstance(value, datetime):
        return {"S": value.isoformat()}
    if isinstance(value, date):
        return {"S": value.isoformat()}
    return {"S": str(value)}


def from_dynamodb_attribute(attribute: dict[str, Any]) -> Any:
    if "S" in attribute:
        return attribute["S"]
    if "N" in attribute:
        number = Decimal(attribute["N"])
        return int(number) if number == number.to_integral_value() else float(number)
    if "BOOL" in attribute:
        return bool(attribute["BOOL"])
    if "NULL" in attribute:
        return None
    if "M" in attribute:
        return from_dynamodb_item(attribute["M"])
    if "L" in attribute:
        return [from_dynamodb_attribute(item) for item in attribute["L"]]
    return None


def from_dynamodb_item(item: dict[str, dict[str, Any]]) -> dict[str, Any]:
    return {key: from_dynamodb_attribute(value) for key, value in item.items()}


def infer_athena_value(field: str, value: str | None) -> Any:
    if value in (None, ""):
        return None
    if field in INTEGER_FIELDS:
        return int(value)
    if field in NUMERIC_FIELDS:
        return float(value)
    if field in TIMESTAMP_FIELDS:
        return value.replace(" ", "T")
    if field in DATE_FIELDS:
        return value
    return value


def json_response(status_code: int, body: dict[str, Any]) -> dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": {"content-type": "application/json"},
        "body": json.dumps(body, separators=(",", ":"), default=str),
    }
