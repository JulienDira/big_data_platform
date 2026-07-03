from __future__ import annotations

import os
from pathlib import Path
import sys

from pyspark.sql import SparkSession

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from registry import get_serving_tables, read_table_sql, render_sql
from utils.env import csv_env, optional_env, required_env
from utils.jdbc import write_postgres_table
from utils.serving import build_serving_render_context, materialize_serving_tables


def build_render_context() -> dict[str, str]:
    return build_serving_render_context(
        base_interval=optional_env("DATAMART_BASE_INTERVAL", "1m"),
        context_intervals=csv_env("DATAMART_CONTEXT_INTERVALS", "15m,1h"),
    )


def main() -> None:
    jdbc_url = required_env("DATAMART_JDBC_URL")
    jdbc_user = required_env("DATAMART_DB_USER")
    jdbc_password = required_env("DATAMART_DB_PASSWORD")
    gold_source = f"{required_env('GOLD_DATABASE')}.{required_env('GOLD_TABLE')}"

    spark = (
        SparkSession.builder.appName("serving-market-datamart")
        .enableHiveSupport()
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel(os.getenv("SPARK_LOG_LEVEL", "WARN"))

    gold = spark.table(gold_source)
    context = build_render_context()

    for table, frame in materialize_serving_tables(
        gold,
        get_serving_tables(),
        read_table_sql,
        render_sql,
        context,
    ):
        write_postgres_table(
            frame,
            url=jdbc_url,
            table=required_env(table.target_env),
            user=jdbc_user,
            password=jdbc_password,
            mode=table.mode,
        )

    spark.stop()


if __name__ == "__main__":
    main()
