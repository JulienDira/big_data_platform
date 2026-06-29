# Jobs

- `raw-consumer`: long-running global Structured Streaming job for the market candles topic, checkpointed in HDFS.
- `bronze-ingestion`: long-running Structured Streaming job from Raw to Bronze, checkpointed in HDFS.
- `silver-transformation`: idempotent full rebuild of the canonical Hive table.
- `gold-indicators`: idempotent full rebuild of the Hive Gold lake table.
- `serving-datamart`: idempotent full rebuild of the PostgreSQL Serving tables from Gold.
- `utils`: shared functions for environment loading, schemas, quality rules, deduplication, indicators, Hive writes and JDBC writes.

All jobs run through `spark-submit --master yarn --deploy-mode cluster`. Runtime
configuration is passed through environment variables by the submission scripts.
Shared Python helpers are packaged into `/tmp/jobs-utils.zip` by the submit
scripts and passed to Spark with `--py-files`.
