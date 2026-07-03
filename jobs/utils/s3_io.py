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


def write_parquet_stream(
    frame: DataFrame,
    path: str,
    checkpoint_path: str,
    partition_columns: tuple[str, ...] = (),
    trigger_interval: str | None = None,
    query_name: str | None = None,
):
    writer = (
        frame.writeStream.format("parquet")
        .outputMode("append")
        .option("path", path)
        .option("checkpointLocation", checkpoint_path)
    )
    if partition_columns:
        writer = writer.partitionBy(*partition_columns)
    if trigger_interval:
        writer = writer.trigger(processingTime=trigger_interval)
    if query_name:
        writer = writer.queryName(query_name)
    return writer.start()
