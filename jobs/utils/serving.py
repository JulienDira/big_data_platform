from __future__ import annotations

from collections.abc import Callable, Iterable

try:
    from pyspark.sql import DataFrame
except ModuleNotFoundError:
    DataFrame = object

from utils.market_schema import GOLD_SOURCE_VIEW


def build_serving_render_context(
    *,
    base_interval: str,
    context_intervals: list[str],
    source_view: str = GOLD_SOURCE_VIEW,
    processing_timestamp: str = "current_timestamp()",
) -> dict[str, str]:
    if len(context_intervals) != 2:
        raise RuntimeError("context_intervals must contain exactly two values")

    return {
        "source_view": source_view,
        "base_interval": base_interval,
        "context_interval_1": context_intervals[0],
        "context_interval_2": context_intervals[1],
        "processing_timestamp": processing_timestamp,
    }


def materialize_serving_tables(
    gold: DataFrame,
    tables: Iterable[object],
    read_table_sql: Callable[[object], str],
    render_sql: Callable[[str, dict[str, str]], str],
    context: dict[str, str],
) -> list[tuple[object, DataFrame]]:
    source_view = context["source_view"]
    gold.createOrReplaceTempView(source_view)

    materialized = []
    for table in tables:
        sql = render_sql(read_table_sql(table), context)
        materialized.append((table, gold.sparkSession.sql(sql)))

    return materialized
