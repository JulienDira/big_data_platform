from __future__ import annotations

try:
    from pyspark.sql import DataFrame
except ModuleNotFoundError:
    DataFrame = object


def write_parquet_dataset(
    frame: DataFrame,
    path: str,
    partition_columns: tuple[str, ...] = (),
    mode: str = "overwrite",
) -> None:
    writer = frame.write.mode(mode).format("parquet")
    if partition_columns:
        writer = writer.partitionBy(*partition_columns)
    writer.save(path)
