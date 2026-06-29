import os
from pathlib import Path

from pyspark.sql import SparkSession
from pyspark.sql.avro.functions import from_avro
from pyspark.sql.functions import (
    col,
    current_timestamp,
    expr,
    hour,
    lit,
    size,
    split,
    to_date,
    when,
)

from raw_config import global_checkpoint_path


def required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def main() -> None:
    spark = SparkSession.builder.appName("raw-consumer-market-candles").getOrCreate()
    spark.sparkContext.setLogLevel(os.getenv("SPARK_LOG_LEVEL", "WARN"))

    schema = Path(required_env("CONTRACT_PATH")).read_text(encoding="utf-8")
    bootstrap_servers = required_env("KAFKA_BOOTSTRAP_SERVERS")
    topic = required_env("KAFKA_TOPIC")
    raw_path = required_env("RAW_PATH")
    checkpoint_base = required_env("RAW_CHECKPOINT_PATH")
    checkpoint = global_checkpoint_path(checkpoint_base)

    kafka = (
        spark.readStream.format("kafka")
        .option("kafka.bootstrap.servers", bootstrap_servers)
        .option("subscribe", topic)
        .option("startingOffsets", "earliest")
        .option("failOnDataLoss", "false")
        .load()
    )

    decoded = kafka.withColumn(
        "data",
        from_avro(
            expr("substring(value, 6, length(value) - 5)"),
            schema,
            {"mode": "PERMISSIVE"},
        ),
    )

    with_key_parts = (
        decoded.withColumn("key_text", col("key").cast("string"))
        .withColumn("key_parts", split(col("key_text"), "\\|"))
    )

    raw = (
        with_key_parts.select(
            lit("kafka").alias("source"),
            col("topic"),
            col("partition"),
            col("offset"),
            col("key_text").alias("key"),
            col("value"),
            col("timestamp").alias("kafka_timestamp"),
            col("timestampType").alias("kafka_timestamp_type"),
            when(size(col("key_parts")) >= 1, col("key_parts").getItem(0))
            .otherwise("_unknown")
            .alias("symbol"),
            when(size(col("key_parts")) >= 2, col("key_parts").getItem(1))
            .otherwise("_unknown")
            .alias("interval"),
            col("data").isNotNull().alias("is_avro_decodable"),
        )
        .withColumn("ingested_at", current_timestamp())
        .withColumn("ingestion_date", to_date("ingested_at"))
        .withColumn("ingestion_hour", hour("ingested_at"))
    )

    query = (
        raw.writeStream.format("parquet")
        .outputMode("append")
        .option("path", raw_path)
        .option("checkpointLocation", checkpoint)
        .partitionBy("symbol", "interval", "ingestion_date", "ingestion_hour")
        .queryName("raw_consumer_market_candles")
        .start()
    )

    query.awaitTermination()


if __name__ == "__main__":
    main()
