from __future__ import annotations

import os
from pathlib import Path
import sys

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, current_timestamp, hour, length, lit, size, split, to_date, when

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from utils.aws_args import option, optional_option
from utils.bronze import decode_avro_payload


def main() -> None:
    stream_name = option("KINESIS_STREAM_NAME")
    region_name = option("AWS_REGION")
    raw_path = option("RAW_OUTPUT_PATH")
    checkpoint_path = option("RAW_CHECKPOINT_PATH")
    contract_path = option("CONTRACT_PATH")
    starting_position = optional_option("KINESIS_STARTING_POSITION", "TRIM_HORIZON")
    trigger_interval = optional_option("RAW_TRIGGER_INTERVAL", "30 seconds")

    spark = SparkSession.builder.appName("raw-market-candles-aws").getOrCreate()
    spark.sparkContext.setLogLevel(os.getenv("SPARK_LOG_LEVEL", "WARN"))

    schema = Path(contract_path).read_text(encoding="utf-8")
    kinesis = (
        spark.readStream.format("kinesis")
        .option("streamName", stream_name)
        .option("region", region_name)
        .option("startingPosition", starting_position)
        .load()
    )

    with_payload = kinesis.withColumn("value", col("data"))
    decoded = decode_avro_payload(with_payload, schema, value_column="value")
    with_key_parts = decoded.withColumn("key_parts", split(col("partitionKey"), "\\|"))

    raw = (
        with_key_parts.select(
            lit("kinesis").alias("source"),
            lit(stream_name).alias("stream_name"),
            col("partitionKey").alias("partition_key"),
            col("sequenceNumber").alias("sequence_number"),
            col("approximateArrivalTimestamp").alias("approximate_arrival_timestamp"),
            col("value"),
            length(col("value")).alias("payload_size_bytes"),
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
        .option("checkpointLocation", checkpoint_path)
        .partitionBy("symbol", "interval", "ingestion_date", "ingestion_hour")
        .trigger(processingTime=trigger_interval)
        .queryName("raw_market_candles_aws")
        .start()
    )
    query.awaitTermination()


if __name__ == "__main__":
    main()
