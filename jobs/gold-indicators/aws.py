from __future__ import annotations

import os
from pathlib import Path
import sys

from pyspark.sql import SparkSession
from pyspark.sql.functions import to_date

JOBS_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(JOBS_ROOT))
sys.path.insert(0, str(JOBS_ROOT / "serving-datamart"))

from registry import get_serving_tables, read_table_sql, render_sql
from utils.aws_args import list_option, option
from utils.indicators import calculate_indicators
from utils.market_schema import GOLD_PARTITIONS, GOLD_SOURCE_COLUMNS
from utils.s3_io import write_parquet_dataset
from utils.serving import build_serving_render_context, materialize_serving_tables


def table_output_path(base_path: str, table_name: str) -> str:
    return f"{base_path.rstrip('/')}/{table_name}"


def main() -> None:
    silver_input_path = option("SILVER_INPUT_PATH")
    gold_output_path = option("GOLD_OUTPUT_PATH")
    trading_gold_output_base_path = option("TRADING_GOLD_OUTPUT_BASE_PATH")

    spark = SparkSession.builder.appName("gold-indicators-aws").getOrCreate()
    spark.sparkContext.setLogLevel(os.getenv("SPARK_LOG_LEVEL", "WARN"))

    silver = spark.read.format("parquet").load(silver_input_path).select(*GOLD_SOURCE_COLUMNS)
    gold = calculate_indicators(silver).withColumn("event_date", to_date("open_time"))
    write_parquet_dataset(gold, gold_output_path, tuple(GOLD_PARTITIONS))

    context = build_serving_render_context(
        base_interval=option("DATAMART_BASE_INTERVAL", "1m"),
        context_intervals=list_option("DATAMART_CONTEXT_INTERVALS", "15m,1h"),
    )

    for table, frame in materialize_serving_tables(
        gold,
        get_serving_tables(),
        read_table_sql,
        render_sql,
        context,
    ):
        write_parquet_dataset(
            frame,
            table_output_path(trading_gold_output_base_path, table.name),
            table.partition_columns,
            table.mode,
        )

    spark.stop()


if __name__ == "__main__":
    main()
