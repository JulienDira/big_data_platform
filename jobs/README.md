# Jobs

- `raw-consumer`: long-running global Structured Streaming job for the market candles topic, checkpointed in HDFS.
- `bronze-ingestion`: long-running Structured Streaming job from Raw to Bronze, checkpointed in HDFS.
- `silver-transformation`: idempotent full rebuild of the canonical Hive table.
- `gold-indicators/main.py`: on-prem entry point for the idempotent rebuild of the Hive Gold lake table.
- `gold-indicators/aws.py`: AWS batch entry point that reads Silver from S3,
  writes Gold indicators to S3, then materializes the `trading_gold.*`
  restitution tables as Parquet datasets.
- `serving-datamart`: idempotent full rebuild of the PostgreSQL Serving tables from Gold.
- `utils`: shared functions for environment loading, schemas, quality rules,
  deduplication, indicators, Serving transformations, Hive writes, S3 Parquet
  writes and JDBC writes.

On-prem jobs run through `spark-submit --master yarn --deploy-mode cluster`.
Runtime configuration is passed through environment variables by the submission
scripts. Shared Python helpers are packaged into `/tmp/jobs-utils.zip` by the
submit scripts and passed to Spark with `--py-files`.

The repo convention is one job folder per logical pipeline step. Environment
entry points live inside that folder: `main.py` for the current on-prem path,
and `aws.py` when an AWS execution path exists.

For `gold-indicators/aws.py`, ship `jobs/utils`,
`jobs/serving-datamart/registry.py` and the SQL templates under
`jobs/serving-datamart/sql/` with the Glue job.
