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
from utils.s3_io import write_parquet_dataset


def main() -> None:
    raw_input_path = option("RAW_INPUT_PATH")
    bronze_output_path = option("BRONZE_OUTPUT_PATH")
    rejected_output_path = option("BRONZE_REJECTED_OUTPUT_PATH")
    contract_path = option("CONTRACT_PATH")
    write_mode = optional_option("WRITE_MODE", "overwrite")

    spark = SparkSession.builder.appName("bronze-market-candles-aws").getOrCreate()
    spark.sparkContext.setLogLevel(os.getenv("SPARK_LOG_LEVEL", "WARN"))

    schema = Path(contract_path).read_text(encoding="utf-8")
    raw = spark.read.format("parquet").load(raw_input_path)
    decoded = decode_avro_payload(raw, schema, value_column="value")

    bronze = build_bronze_valid(decoded)
    rejected = build_bronze_rejected(decoded)

    write_parquet_dataset(bronze, bronze_output_path, BRONZE_PARTITIONS, write_mode)
    write_parquet_dataset(rejected, rejected_output_path, (), write_mode)
    spark.stop()


if __name__ == "__main__":
    main()
