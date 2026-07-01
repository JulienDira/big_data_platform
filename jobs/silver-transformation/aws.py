from __future__ import annotations

import os
from pathlib import Path
import sys

from pyspark.sql import SparkSession

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from utils.aws_args import option, optional_option
from utils.market_schema import SILVER_PARTITIONS
from utils.s3_io import write_parquet_dataset
from utils.silver import build_silver


def main() -> None:
    bronze_input_path = option("BRONZE_INPUT_PATH")
    silver_output_path = option("SILVER_OUTPUT_PATH")
    write_mode = optional_option("WRITE_MODE", "overwrite")

    spark = SparkSession.builder.appName("silver-market-candles-aws").getOrCreate()
    spark.sparkContext.setLogLevel(os.getenv("SPARK_LOG_LEVEL", "WARN"))

    bronze = spark.read.format("parquet").load(bronze_input_path)
    silver = build_silver(bronze)
    write_parquet_dataset(silver, silver_output_path, tuple(SILVER_PARTITIONS), write_mode)
    spark.stop()


if __name__ == "__main__":
    main()
