import os
from pathlib import Path

from pyspark.sql import SparkSession
from pyspark.sql.avro.functions import from_avro
from pyspark.sql.functions import (
    col,
    dayofmonth,
    expr,
    month,
    to_date,
    year,
)
from pyspark.sql.types import (
    BinaryType,
    DateType,
    IntegerType,
    LongType,
    StringType,
    StructField,
    StructType,
    TimestampType,
)


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

    # Confluent Avro payloads start with a magic byte and a four-byte schema ID.
    decoded = raw.withColumn(
        "data",
        from_avro(
            expr("substring(value, 6, length(value) - 5)"),
            schema,
            {"mode": "PERMISSIVE"},
        ),
    )

    valid = (
        decoded.filter(col("data").isNotNull())
        .select("data.*")
        .withColumn("event_date", to_date("open_time"))
        .withColumn("year", year("open_time"))
        .withColumn("month", month("open_time"))
        .withColumn("day", dayofmonth("open_time"))
        .withWatermark("open_time", watermark_delay)
        .dropDuplicates(["event_id"])
    )

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

    invalid = decoded.filter(col("data").isNull()).select(col("key"), col("value"))
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
