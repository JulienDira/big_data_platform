from __future__ import annotations

import json
import os
import time

from model import normalize_kline


def required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def csv_env(name: str) -> list[str]:
    return [item.strip().upper() for item in required_env(name).split(",") if item.strip()]


def positive_int_env(name: str, default: int, *, maximum: int | None = None) -> int:
    raw_value = os.getenv(name, str(default))
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer") from exc
    if value < 1:
        raise RuntimeError(f"{name} must be greater than zero")
    if maximum is not None and value > maximum:
        raise RuntimeError(f"{name} must be less than or equal to {maximum}")
    return value


def build_partition_key(candle: dict) -> str:
    return f"{candle['symbol']}|{candle['interval']}"


def fetch_latest(session, base_url: str, symbol: str, interval: str) -> dict:
    response = session.get(
        f"{base_url}/api/v3/klines",
        params={"symbol": symbol, "interval": interval, "limit": 2},
        timeout=10,
    )
    response.raise_for_status()
    rows = response.json()
    if not isinstance(rows, list) or not rows:
        raise ValueError(f"Unexpected Binance response: {json.dumps(rows)[:200]}")

    now_ms = int(time.time() * 1000)
    closed_rows = [row for row in rows if int(row[6]) < now_ms]
    return normalize_kline(
        symbol,
        interval,
        (closed_rows or rows)[-1],
        now_ms=now_ms,
    )
