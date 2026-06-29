def normalize_kline(symbol: str, interval: str, row: list, now_ms: int) -> dict:
    open_time = int(row[0])
    return {
        "event_id": f"binance:{symbol}:{interval}:{open_time}",
        "source": "binance-rest",
        "symbol": symbol,
        "interval": interval,
        "open_time": open_time,
        "close_time": int(row[6]),
        "open": float(row[1]),
        "high": float(row[2]),
        "low": float(row[3]),
        "close": float(row[4]),
        "volume": float(row[5]),
        "quote_asset_volume": float(row[7]),
        "number_of_trades": int(row[8]),
        "taker_buy_base_asset_volume": float(row[9]),
        "taker_buy_quote_asset_volume": float(row[10]),
        "is_closed": int(row[6]) < now_ms,
        "ingested_at": now_ms,
    }

