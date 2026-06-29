from __future__ import annotations

from pyspark.sql import DataFrame, Window
from pyspark.sql.functions import col, row_number


def latest_by_key(
    frame: DataFrame,
    key_columns: list[str],
    order_columns: list[str],
) -> DataFrame:
    window = Window.partitionBy(*key_columns).orderBy(
        *[col(column).desc() for column in order_columns]
    )
    return (
        frame.withColumn("_row_number", row_number().over(window))
        .filter(col("_row_number") == 1)
        .drop("_row_number")
    )
