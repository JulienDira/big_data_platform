from __future__ import annotations

from pyspark.sql import DataFrame

from utils.dedup import latest_by_key
from utils.market_schema import SILVER_COLUMNS
from utils.quality import apply_silver_quality_rules


def build_silver(bronze: DataFrame) -> DataFrame:
    clean = apply_silver_quality_rules(bronze)
    deduplicated = latest_by_key(
        clean,
        key_columns=["symbol", "interval", "open_time"],
        order_columns=["ingested_at", "event_id"],
    )
    return deduplicated.select(*SILVER_COLUMNS)
