from __future__ import annotations

import logging
import os
from typing import Any

from serving_common import (
    ApiError,
    BadRequest,
    DEFAULT_INTERVALS,
    DEFAULT_SYMBOLS,
    NotFound,
    aws_client,
    bounded_limit,
    csv_values,
    decode_next_token,
    encode_next_token,
    from_dynamodb_item,
    get_athena_page,
    infer_athena_value,
    json_response,
    parse_date_filter,
    parse_timestamp_filter,
    require_allowed,
    required_env,
    sql_string,
    start_athena_query,
    wait_for_athena_query,
)


LOGGER = logging.getLogger(__name__)

HISTORY_FIELDS = (
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
)

SIGNAL_FIELDS = (
    "symbol",
    "base_interval",
    "open_time",
    "close_time",
    "close",
    "volume",
    "rsi_14_1m",
    "macd_1m",
    "trend_15m",
    "rsi_14_15m",
    "macd_15m",
    "trend_1h",
    "rsi_14_1h",
    "macd_1h",
    "signal_score",
    "signal_label",
    "generated_at",
)

DAILY_SUMMARY_FIELDS = (
    "symbol",
    "event_date",
    "open_price",
    "close_price",
    "high_price",
    "low_price",
    "daily_volume",
    "avg_rsi_14",
    "avg_macd",
    "volatility_score",
    "generated_at",
)


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    try:
        return handle_request(event)
    except ApiError as exc:
        return json_response(exc.status_code, {"error": exc.message})
    except Exception:
        LOGGER.exception("Unhandled API error")
        return json_response(500, {"error": "Internal server error"})


def handle_request(event: dict[str, Any]) -> dict[str, Any]:
    method = _method(event)
    path = _path(event)
    params = event.get("queryStringParameters") or {}

    if method != "GET":
        raise BadRequest("Only GET is supported")
    if path == "/health":
        return json_response(200, health_body())
    if path == "/metrics/latest":
        return json_response(200, latest_metric(params))
    if path == "/metrics/history":
        return json_response(200, athena_items("history", params))
    if path == "/signals":
        return json_response(200, athena_items("signals", params))
    if path == "/daily-summary":
        return json_response(200, athena_items("daily-summary", params))

    raise NotFound(f"Unknown route: {path}")


def health_body() -> dict[str, Any]:
    return {
        "status": "ok",
        "service": "market-data-api",
        "dynamodb_table_configured": bool(os.getenv("DYNAMODB_TABLE_NAME")),
        "athena_workgroup_configured": bool(os.getenv("ATHENA_WORKGROUP")),
    }


def latest_metric(params: dict[str, str]) -> dict[str, Any]:
    symbol = validate_symbol(params.get("symbol"))
    interval = validate_interval(params.get("interval"))
    table_name = required_env("DYNAMODB_TABLE_NAME")
    client = aws_client("dynamodb")
    result = client.get_item(
        TableName=table_name,
        Key={"symbol": {"S": symbol}, "interval": {"S": interval}},
        ConsistentRead=False,
    )
    item = result.get("Item")
    if not item:
        raise NotFound("Latest metric not found")
    return {"item": from_dynamodb_item(item)}


def athena_items(kind: str, params: dict[str, str]) -> dict[str, Any]:
    token = decode_next_token(params.get("next_token"))
    limit = bounded_limit(
        params.get("limit"),
        default=int(os.getenv("HISTORY_DEFAULT_LIMIT", "100")),
        maximum=int(os.getenv("HISTORY_MAX_LIMIT", "500")),
    )
    athena = aws_client("athena")
    if token:
        query_execution_id = token["query_execution_id"]
        page = get_athena_page(athena, query_execution_id, limit, token["token"])
        return page_to_response(query_execution_id, page)

    query = build_query(kind, params, limit)
    query_execution_id = start_athena_query(athena, query)
    wait_for_athena_query(athena, query_execution_id)
    page = get_athena_page(athena, query_execution_id, limit)
    return page_to_response(query_execution_id, page)


def build_query(kind: str, params: dict[str, str], limit: int) -> str:
    database = required_env("ATHENA_DATABASE")
    if kind == "history":
        return build_history_query(database, params, limit)
    if kind == "signals":
        return build_signals_query(database, params, limit)
    if kind == "daily-summary":
        return build_daily_summary_query(database, params, limit)
    raise BadRequest(f"Unsupported query kind: {kind}")


def build_history_query(database: str, params: dict[str, str], limit: int) -> str:
    symbol = validate_symbol(params.get("symbol"))
    interval = validate_interval(params.get("interval"))
    where = [
        f"symbol = {sql_string(symbol)}",
        f"interval = {sql_string(interval)}",
    ]
    add_timestamp_filters(where, "open_time", params)
    return fixed_select(
        HISTORY_FIELDS,
        database,
        "market_indicators",
        where,
        "open_time DESC",
        limit,
    )


def build_signals_query(database: str, params: dict[str, str], limit: int) -> str:
    symbol = validate_symbol(params.get("symbol"))
    where = [f"symbol = {sql_string(symbol)}"]
    add_timestamp_filters(where, "open_time", params)
    return fixed_select(
        SIGNAL_FIELDS,
        database,
        "market_multitimeframe_signals",
        where,
        "open_time DESC",
        limit,
    )


def build_daily_summary_query(database: str, params: dict[str, str], limit: int) -> str:
    symbol = validate_symbol(params.get("symbol"))
    where = [f"symbol = {sql_string(symbol)}"]
    start_date = parse_date_filter(params.get("from"), "from")
    end_date = parse_date_filter(params.get("to"), "to")
    if start_date:
        where.append(f"event_date >= DATE {sql_string(start_date)}")
    if end_date:
        where.append(f"event_date <= DATE {sql_string(end_date)}")
    return fixed_select(
        DAILY_SUMMARY_FIELDS,
        database,
        "market_daily_summary",
        where,
        "event_date DESC",
        limit,
    )


def fixed_select(
    fields: tuple[str, ...],
    database: str,
    table: str,
    where: list[str],
    order_by: str,
    limit: int,
) -> str:
    selected = ", ".join(fields)
    filters = " AND ".join(where)
    return (
        f'SELECT {selected} FROM "{database}"."{table}" '
        f"WHERE {filters} ORDER BY {order_by} LIMIT {limit}"
    )


def add_timestamp_filters(where: list[str], column: str, params: dict[str, str]) -> None:
    start = parse_timestamp_filter(params.get("from"), "from")
    end = parse_timestamp_filter(params.get("to"), "to")
    if start:
        where.append(f"{column} >= TIMESTAMP {sql_string(start)}")
    if end:
        where.append(f"{column} <= TIMESTAMP {sql_string(end)}")


def page_to_response(query_execution_id: str, page: dict[str, Any]) -> dict[str, Any]:
    rows = page.get("ResultSet", {}).get("Rows", [])
    if not rows:
        return {"items": [], "next_token": None}

    headers = [
        column["Name"]
        for column in page.get("ResultSet", {}).get("ResultSetMetadata", {}).get(
            "ColumnInfo", []
        )
    ]
    if not headers:
        headers = [cell.get("VarCharValue", "") for cell in rows[0].get("Data", [])]
    data_rows = rows
    first_row_values = [cell.get("VarCharValue", "") for cell in rows[0].get("Data", [])]
    if first_row_values == headers:
        data_rows = rows[1:]

    items = [athena_row_to_item(headers, row) for row in data_rows]
    return {
        "items": items,
        "next_token": encode_next_token(query_execution_id, page.get("NextToken")),
    }


def athena_row_to_item(headers: list[str], row: dict[str, Any]) -> dict[str, Any]:
    values = row.get("Data", [])
    item: dict[str, Any] = {}
    for index, field in enumerate(headers):
        value = values[index].get("VarCharValue") if index < len(values) else None
        item[field] = infer_athena_value(field, value)
    return item


def validate_symbol(value: str | None) -> str:
    return require_allowed(
        value,
        "symbol",
        csv_values(os.getenv("ALLOWED_SYMBOLS"), DEFAULT_SYMBOLS),
    )


def validate_interval(value: str | None) -> str:
    return require_allowed(
        value,
        "interval",
        csv_values(os.getenv("ALLOWED_INTERVALS"), DEFAULT_INTERVALS),
    )


def _method(event: dict[str, Any]) -> str:
    return (
        event.get("requestContext", {})
        .get("http", {})
        .get("method", event.get("httpMethod", ""))
        .upper()
    )


def _path(event: dict[str, Any]) -> str:
    return event.get("rawPath") or event.get("path") or "/"
