from __future__ import annotations

import os
from pathlib import Path
import sys

from pyspark.sql import SparkSession

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from utils.aws_args import option, optional_option
from utils.bronze import (
    BRONZE_PARTITIONS,
    build_bronze_rejected,
    build_bronze_valid,
    decode_avro_payload,
)
from utils.market_schema import AWS_RAW_MARKET_CANDLES_SCHEMA
from utils.s3_io import write_parquet_stream


def main() -> None:
    raw_input_path = option("RAW_INPUT_PATH")
    bronze_output_path = option("BRONZE_OUTPUT_PATH")
    rejected_output_path = option("BRONZE_REJECTED_OUTPUT_PATH")
    bronze_checkpoint_path = option("BRONZE_CHECKPOINT_PATH")
    rejected_checkpoint_path = option("BRONZE_REJECTED_CHECKPOINT_PATH")
    contract_path = option("CONTRACT_PATH")
    max_files_per_trigger = optional_option("BRONZE_MAX_FILES_PER_TRIGGER", "100")
    trigger_interval = optional_option("BRONZE_TRIGGER_INTERVAL", "30 seconds")
    watermark_delay = optional_option("BRONZE_WATERMARK_DELAY", "2 days")

    spark = SparkSession.builder.appName("bronze-market-candles-aws").getOrCreate()
    spark.sparkContext.setLogLevel(os.getenv("SPARK_LOG_LEVEL", "WARN"))

    schema = Path(contract_path).read_text(encoding="utf-8")
    raw = (
        spark.readStream.schema(AWS_RAW_MARKET_CANDLES_SCHEMA)
        .format("parquet")
        .option("basePath", raw_input_path)
        .option("maxFilesPerTrigger", max_files_per_trigger)
        .load(raw_input_path)
    )
    decoded = decode_avro_payload(raw, schema, value_column="value")

    bronze = build_bronze_valid(decoded, watermark_delay=watermark_delay)
    rejected = build_bronze_rejected(decoded)

    bronze_query = write_parquet_stream(
        bronze,
        bronze_output_path,
        bronze_checkpoint_path,
        BRONZE_PARTITIONS,
        trigger_interval,
        "bronze_market_candles_aws",
    )
    rejected_query = write_parquet_stream(
        rejected,
        rejected_output_path,
        rejected_checkpoint_path,
        (),
        trigger_interval,
        "bronze_market_candles_aws_rejected",
    )

    try:
        spark.streams.awaitAnyTermination()
    finally:
        bronze_query.stop()
        rejected_query.stop()
        spark.stop()


if __name__ == "__main__":
    main()
