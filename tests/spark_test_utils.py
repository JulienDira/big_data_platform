from pyspark.sql import SparkSession


def create_local_spark(app_name: str) -> SparkSession:
    return (
        SparkSession.builder.master("local[1]")
        .appName(app_name)
        .config("spark.submit.deployMode", "client")
        .config("spark.ui.enabled", "false")
        .config("spark.eventLog.enabled", "false")
        .config("spark.hadoop.fs.defaultFS", "file:///")
        .config("spark.sql.warehouse.dir", "file:///tmp/spark-warehouse")
        .config("spark.sql.shuffle.partitions", "1")
        .config("spark.default.parallelism", "1")
        .getOrCreate()
    )
