import os
from pathlib import Path
import sys

from pyspark.sql import SparkSession

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from utils.env import required_env
from utils.hive_io import write_hive_table
from utils.market_schema import SILVER_PARTITIONS
from utils.silver import build_silver


def main() -> None:
    database = required_env("SILVER_DATABASE")
    table = required_env("SILVER_TABLE")
    bronze_path = required_env("BRONZE_PATH")

    spark = (
        SparkSession.builder.appName("silver-market-candles")
        .enableHiveSupport()
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel(os.getenv("SPARK_LOG_LEVEL", "WARN"))

    bronze = spark.read.format("parquet").load(bronze_path)
    silver = build_silver(bronze)
    write_hive_table(silver, database, table, SILVER_PARTITIONS)
    spark.stop()


if __name__ == "__main__":
    main()
