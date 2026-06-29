from __future__ import annotations

from pyspark.sql import DataFrame, SparkSession


def create_database(spark: SparkSession, database: str) -> None:
    spark.sql(f"CREATE DATABASE IF NOT EXISTS `{database}`")


def write_hive_table(
    frame: DataFrame,
    database: str,
    table: str,
    partition_columns: list[str],
    mode: str = "overwrite",
) -> None:
    create_database(frame.sparkSession, database)
    (
        frame.write.mode(mode)
        .format("parquet")
        .partitionBy(*partition_columns)
        .saveAsTable(f"`{database}`.`{table}`")
    )
