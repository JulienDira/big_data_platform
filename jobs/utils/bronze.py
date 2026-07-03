from __future__ import annotations

from pyspark.sql import DataFrame
from pyspark.sql.avro.functions import from_avro
from pyspark.sql.functions import col, dayofmonth, expr, lit, month, to_date, year


BRONZE_PARTITIONS = ("event_date", "symbol", "interval")


def decode_avro_payload(
    frame: DataFrame,
    schema: str,
    *,
    value_column: str = "value",
    output_column: str = "data",
    confluent_header: bool = False,
) -> DataFrame:
    payload = (
        expr(f"substring({value_column}, 6, length({value_column}) - 5)")
        if confluent_header
        else col(value_column)
    )
    return frame.withColumn(output_column, from_avro(payload, schema, {"mode": "PERMISSIVE"}))


def build_bronze_valid(
    decoded: DataFrame,
    *,
    watermark_delay: str | None = None,
) -> DataFrame:
    valid = (
        decoded.filter(col("data").isNotNull())
        .select("data.*")
        .withColumn("event_date", to_date("open_time"))
        .withColumn("year", year("open_time"))
        .withColumn("month", month("open_time"))
        .withColumn("day", dayofmonth("open_time"))
    )
    if watermark_delay:
        valid = valid.withWatermark("open_time", watermark_delay)
    return valid.dropDuplicates(["event_id"])


def build_bronze_rejected(decoded: DataFrame) -> DataFrame:
    rejected = decoded.filter(col("data").isNull()).withColumn(
        "bronze_error_reason",
        lit("avro_decode_failed"),
    )
    columns = [
        column
        for column in (
            "source",
            "topic",
            "partition",
            "offset",
            "stream_name",
            "partition_key",
            "sequence_number",
            "key",
            "value",
            "kafka_timestamp",
            "kafka_timestamp_type",
            "approximate_arrival_timestamp",
            "ingested_at",
            "symbol",
            "interval",
            "ingestion_date",
            "ingestion_hour",
            "is_avro_decodable",
            "bronze_error_reason",
        )
        if column in rejected.columns
    ]
    return rejected.select(*columns)
