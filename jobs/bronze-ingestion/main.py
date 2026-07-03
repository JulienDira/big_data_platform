import os
from pathlib import Path
import sys

from pyspark.sql import SparkSession
from pyspark.sql.functions import col
from pyspark.sql.types import (
    BinaryType,
    BooleanType,
    DateType,
    IntegerType,
    LongType,
    StringType,
    StructField,
    StructType,
    TimestampType,
)

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from utils.bronze import build_bronze_rejected, build_bronze_valid, decode_avro_payload


RAW_SCHEMA = StructType(
    [
        StructField("source", StringType(), False),
        StructField("topic", StringType(), False),
        StructField("partition", IntegerType(), False),
        StructField("offset", LongType(), False),
        StructField("key", StringType(), True),
        StructField("value", BinaryType(), False),
        StructField("kafka_timestamp", TimestampType(), True),
        StructField("kafka_timestamp_type", IntegerType(), True),
        StructField("ingested_at", TimestampType(), False),
        StructField("symbol", StringType(), False),
        StructField("interval", StringType(), False),
        StructField("is_avro_decodable", BooleanType(), True),
        StructField("ingestion_date", DateType(), False),
        StructField("ingestion_hour", IntegerType(), False),
    ]
)


def required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def main() -> None:
    spark = SparkSession.builder.appName("bronze-market-candles").getOrCreate()
    spark.sparkContext.setLogLevel(os.getenv("SPARK_LOG_LEVEL", "WARN"))

    schema = Path(required_env("CONTRACT_PATH")).read_text(encoding="utf-8")
    bootstrap_servers = required_env("KAFKA_BOOTSTRAP_SERVERS")
    error_topic = required_env("KAFKA_ERROR_TOPIC")
    raw_path = required_env("RAW_PATH")
    bronze_path = required_env("BRONZE_PATH")
    checkpoint = required_env("BRONZE_CHECKPOINT_PATH")
    trigger_interval = required_env("BRONZE_TRIGGER_INTERVAL")
    watermark_delay = required_env("BRONZE_WATERMARK_DELAY")

    raw = (
        spark.readStream.schema(RAW_SCHEMA)
        .format("parquet")
        .option("basePath", raw_path)
        .load(raw_path)
    )

    decoded = decode_avro_payload(
        raw,
        schema,
        value_column="value",
        confluent_header=True,
    )

    valid = build_bronze_valid(decoded, watermark_delay=watermark_delay)

    bronze_query = (
        valid.writeStream.format("parquet")
        .outputMode("append")
        .option("path", bronze_path)
        .option("checkpointLocation", checkpoint)
        .partitionBy("event_date", "symbol", "interval")
        .trigger(processingTime=trigger_interval)
        .queryName("bronze_market_candles")
        .start()
    )

    invalid = build_bronze_rejected(decoded).select(col("key"), col("value"))
    error_query = (
        invalid.writeStream.format("kafka")
        .option("kafka.bootstrap.servers", bootstrap_servers)
        .option("topic", error_topic)
        .option("checkpointLocation", f"{checkpoint}_errors")
        .trigger(processingTime=trigger_interval)
        .queryName("bronze_market_candles_errors")
        .start()
    )

    spark.streams.awaitAnyTermination()
    bronze_query.stop()
    error_query.stop()


if __name__ == "__main__":
    main()
