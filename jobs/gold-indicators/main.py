import os
from pathlib import Path
import sys

from pyspark.sql import SparkSession
from pyspark.sql.functions import to_date

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from utils.env import required_env
from utils.hive_io import write_hive_table
from utils.indicators import calculate_indicators
from utils.market_schema import GOLD_PARTITIONS, GOLD_SOURCE_COLUMNS


def main() -> None:
    gold_database = required_env("GOLD_DATABASE")
    gold_table = required_env("GOLD_TABLE")

    spark = (
        SparkSession.builder.appName("gold-market-indicators")
        .enableHiveSupport()
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel(os.getenv("SPARK_LOG_LEVEL", "WARN"))

    source = f"{required_env('SILVER_DATABASE')}.{required_env('SILVER_TABLE')}"
    candles = spark.table(source).select(*GOLD_SOURCE_COLUMNS)
    gold = calculate_indicators(candles).withColumn("event_date", to_date("open_time"))

    write_hive_table(gold, gold_database, gold_table, GOLD_PARTITIONS)
    spark.stop()


if __name__ == "__main__":
    main()
