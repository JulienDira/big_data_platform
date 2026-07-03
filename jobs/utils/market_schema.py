try:
    from pyspark.sql.types import (
        BinaryType,
        BooleanType,
        DateType,
        DoubleType,
        IntegerType,
        LongType,
        StringType,
        StructField,
        StructType,
        TimestampType,
    )
except ModuleNotFoundError:
    BinaryType = BooleanType = DateType = DoubleType = IntegerType = LongType = None
    StringType = StructField = StructType = TimestampType = None


SILVER_COLUMNS = [
    "event_id",
    "source",
    "symbol",
    "interval",
    "open_time",
    "close_time",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "quote_asset_volume",
    "number_of_trades",
    "taker_buy_base_asset_volume",
    "taker_buy_quote_asset_volume",
    "is_closed",
    "ingested_at",
    "event_date",
]

SILVER_PARTITIONS = ["event_date", "symbol", "interval"]

GOLD_COLUMNS = [
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
]

GOLD_PARTITIONS = ["event_date", "symbol", "interval"]

if StructType is not None:
    AWS_RAW_MARKET_CANDLES_SCHEMA = StructType(
        [
            StructField("source", StringType(), False),
            StructField("stream_name", StringType(), False),
            StructField("partition_key", StringType(), True),
            StructField("sequence_number", StringType(), True),
            StructField("approximate_arrival_timestamp", TimestampType(), True),
            StructField("value", BinaryType(), False),
            StructField("payload_size_bytes", IntegerType(), True),
            StructField("symbol", StringType(), False),
            StructField("interval", StringType(), False),
            StructField("is_avro_decodable", BooleanType(), True),
            StructField("ingested_at", TimestampType(), False),
            StructField("ingestion_date", DateType(), False),
            StructField("ingestion_hour", IntegerType(), False),
        ]
    )

    GOLD_SCHEMA = StructType(
        [
            StructField("symbol", StringType(), False),
            StructField("interval", StringType(), False),
            StructField("open_time", TimestampType(), False),
            StructField("close_time", TimestampType(), False),
            StructField("open", DoubleType(), False),
            StructField("high", DoubleType(), False),
            StructField("low", DoubleType(), False),
            StructField("close", DoubleType(), False),
            StructField("volume", DoubleType(), False),
            StructField("ema_12", DoubleType(), True),
            StructField("ema_26", DoubleType(), True),
            StructField("macd", DoubleType(), True),
            StructField("rsi_14", DoubleType(), True),
            StructField("bollinger_middle", DoubleType(), True),
            StructField("bollinger_upper", DoubleType(), True),
            StructField("bollinger_lower", DoubleType(), True),
        ]
    )
else:
    AWS_RAW_MARKET_CANDLES_SCHEMA = None
    GOLD_SCHEMA = None

GOLD_SOURCE_COLUMNS = [
    "symbol",
    "interval",
    "open_time",
    "close_time",
    "open",
    "high",
    "low",
    "close",
    "volume",
]

GOLD_SOURCE_VIEW = "gold_market_indicators"
