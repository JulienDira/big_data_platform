from pyspark.sql import DataFrame
from pyspark.sql.functions import col


def filter_closed_candles(frame: DataFrame) -> DataFrame:
    return frame.filter(col("is_closed"))


def apply_ohlcv_quality_rules(frame: DataFrame) -> DataFrame:
    return frame.filter(
        col("event_id").isNotNull()
        & col("source").isNotNull()
        & col("symbol").isNotNull()
        & col("interval").isNotNull()
        & col("open_time").isNotNull()
        & col("close_time").isNotNull()
        & col("ingested_at").isNotNull()
        & col("event_date").isNotNull()
        & (col("open") > 0)
        & (col("high") > 0)
        & (col("low") > 0)
        & (col("close") > 0)
        & (col("high") >= col("low"))
        & (col("high") >= col("open"))
        & (col("high") >= col("close"))
        & (col("low") <= col("open"))
        & (col("low") <= col("close"))
        & (col("volume") >= 0)
        & (col("quote_asset_volume") >= 0)
        & (col("number_of_trades") >= 0)
        & (col("taker_buy_base_asset_volume") >= 0)
        & (col("taker_buy_quote_asset_volume") >= 0)
    )


def apply_silver_quality_rules(frame: DataFrame) -> DataFrame:
    return apply_ohlcv_quality_rules(filter_closed_candles(frame))

