from pyspark.sql import DataFrame, Window
from pyspark.sql import functions as F
from pyspark.sql.window import WindowSpec

from utils.market_schema import GOLD_COLUMNS


PARTITION_COLUMNS = ["symbol", "interval"]
ORDER_COLUMNS = ["open_time", "close_time"]


def _with_ema(
    frame: DataFrame,
    *,
    source_column: str,
    output_column: str,
    alpha: float,
    start_index_column: str,
    sequence_column: str,
    window_spec: WindowSpec,
) -> DataFrame:
    beta = 1.0 - alpha
    weighted_source = F.when(
        F.col(sequence_column) > F.col(start_index_column),
        F.col(source_column) / F.pow(F.lit(beta), F.col(sequence_column)),
    )
    weighted_sum = F.sum(weighted_source).over(window_spec)
    first_value = F.first(
        F.when(F.col(sequence_column) == F.col(start_index_column), F.col(source_column)),
        ignorenulls=True,
    ).over(window_spec)

    ema = (
        F.pow(F.lit(beta), F.col(sequence_column) - F.col(start_index_column))
        * first_value
    ) + (
        F.lit(alpha)
        * F.pow(F.lit(beta), F.col(sequence_column))
        * F.coalesce(weighted_sum, F.lit(0.0))
    )

    return frame.withColumn(
        output_column,
        F.when(F.col(sequence_column) >= F.col(start_index_column), ema),
    )


def calculate_indicators(frame: DataFrame) -> DataFrame:
    ordered_window = Window.partitionBy(*PARTITION_COLUMNS).orderBy(*ORDER_COLUMNS)
    rows_to_current = ordered_window.rowsBetween(Window.unboundedPreceding, Window.currentRow)
    bollinger_window = ordered_window.rowsBetween(-19, Window.currentRow)

    indexed = (
        frame.withColumn("close", F.col("close").cast("double"))
        .withColumn("_row_index", F.row_number().over(ordered_window) - F.lit(1))
        .withColumn("_previous_close", F.lag("close").over(ordered_window))
        .withColumn("_first_close_index", F.lit(0))
    )

    with_ema = _with_ema(
        indexed,
        source_column="close",
        output_column="ema_12",
        alpha=2.0 / 13.0,
        start_index_column="_first_close_index",
        sequence_column="_row_index",
        window_spec=rows_to_current,
    )

    with_ema = _with_ema(
        with_ema,
        source_column="close",
        output_column="ema_26",
        alpha=2.0 / 27.0,
        start_index_column="_first_close_index",
        sequence_column="_row_index",
        window_spec=rows_to_current,
    )

    with_moves = (
        with_ema.withColumn("macd", F.col("ema_12") - F.col("ema_26"))
        .withColumn("_delta", F.col("close") - F.col("_previous_close"))
        .withColumn("_gain", F.greatest(F.col("_delta"), F.lit(0.0)))
        .withColumn("_loss", F.greatest(-F.col("_delta"), F.lit(0.0)))
        .withColumn("_first_move_index", F.lit(1))
    )

    with_rsi = _with_ema(
        with_moves,
        source_column="_gain",
        output_column="_avg_gain",
        alpha=1.0 / 14.0,
        start_index_column="_first_move_index",
        sequence_column="_row_index",
        window_spec=rows_to_current,
    )
    with_rsi = _with_ema(
        with_rsi,
        source_column="_loss",
        output_column="_avg_loss",
        alpha=1.0 / 14.0,
        start_index_column="_first_move_index",
        sequence_column="_row_index",
        window_spec=rows_to_current,
    ).withColumn(
        "rsi_14",
        F.when(
            (F.col("_avg_loss") == 0.0) & (F.col("_avg_gain") > 0.0),
            F.lit(100.0),
        )
        .when(
            (F.col("_avg_loss") == 0.0) & (F.col("_avg_gain") == 0.0),
            F.lit(50.0),
        )
        .otherwise(100.0 - (100.0 / (1.0 + (F.col("_avg_gain") / F.col("_avg_loss"))))),
    )

    with_bollinger = (
        with_rsi.withColumn("bollinger_middle", F.avg("close").over(bollinger_window))
        .withColumn("_bollinger_deviation", F.stddev_pop("close").over(bollinger_window))
        .withColumn(
            "bollinger_upper",
            F.col("bollinger_middle") + (F.lit(2.0) * F.col("_bollinger_deviation")),
        )
        .withColumn(
            "bollinger_lower",
            F.col("bollinger_middle") - (F.lit(2.0) * F.col("_bollinger_deviation")),
        )
    )

    return with_bollinger.select(*GOLD_COLUMNS)
