from __future__ import annotations

import os
import time
from decimal import Decimal
from typing import Any

from serving_common import (
    aws_client,
    get_athena_page,
    required_env,
    start_athena_query,
    to_decimal,
    to_dynamodb_attribute,
    wait_for_athena_query,
)


LATEST_FIELDS = (
    "symbol",
    "interval",
    "open_time",
    "close_time",
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
    "event_date",
    "updated_at",
)

NUMERIC_LATEST_FIELDS = {
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
}


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    athena = aws_client("athena")
    dynamodb = aws_client("dynamodb")
    query_execution_id = start_athena_query(athena, latest_metrics_query())
    wait_for_athena_query(athena, query_execution_id)
    page = get_athena_page(
        athena,
        query_execution_id,
        int(os.getenv("PROJECTION_QUERY_LIMIT", "1000")),
    )
    rows = athena_rows(page)
    ttl_days = int(os.getenv("CACHE_TTL_DAYS", "7"))
    now_epoch = int(time.time())

    for row in rows:
        dynamodb.put_item(
            TableName=required_env("DYNAMODB_TABLE_NAME"),
            Item=latest_metric_row_to_item(row, ttl_days=ttl_days, now_epoch=now_epoch),
        )

    return {"projected_items": len(rows), "query_execution_id": query_execution_id}


def latest_metrics_query() -> str:
    database = required_env("ATHENA_DATABASE")
    selected = ", ".join(LATEST_FIELDS)
    return f'SELECT {selected} FROM "{database}"."market_indicators_latest"'


def athena_rows(page: dict[str, Any]) -> list[dict[str, Any]]:
    rows = page.get("ResultSet", {}).get("Rows", [])
    if not rows:
        return []
    headers = [cell.get("VarCharValue", "") for cell in rows[0].get("Data", [])]
    return [athena_row(headers, row) for row in rows[1:]]


def athena_row(headers: list[str], row: dict[str, Any]) -> dict[str, Any]:
    values = row.get("Data", [])
    item: dict[str, Any] = {}
    for index, field in enumerate(headers):
        value = values[index].get("VarCharValue") if index < len(values) else None
        item[field] = parse_latest_value(field, value)
    return item


def parse_latest_value(field: str, value: str | None) -> str | Decimal | None:
    if value in (None, ""):
        return None
    if field in NUMERIC_LATEST_FIELDS:
        return to_decimal(value)
    return value


def latest_metric_row_to_item(
    row: dict[str, Any],
    *,
    ttl_days: int,
    now_epoch: int,
) -> dict[str, dict[str, Any]]:
    item = {field: to_dynamodb_attribute(row.get(field)) for field in LATEST_FIELDS}
    item["expires_at_epoch"] = to_dynamodb_attribute(now_epoch + ttl_days * 24 * 60 * 60)
    return item
