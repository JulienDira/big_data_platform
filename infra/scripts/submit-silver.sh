#!/usr/bin/env bash
set -euo pipefail

: "${SPARK_VERSION:?}"
: "${HIVE_VERSION:?}"
: "${BRONZE_PATH:?}"
: "${SILVER_DATABASE:?}"
: "${SILVER_TABLE:?}"

UTILS_ZIP="/tmp/jobs-utils.zip"
python3 /workspace/infra/scripts/package-job-utils.py "${UTILS_ZIP}"

exec spark-submit \
  --master yarn \
  --deploy-mode cluster \
  --name silver-market-candles \
  --py-files "${UTILS_ZIP}" \
  --packages "org.apache.spark:spark-avro_2.12:${SPARK_VERSION}" \
  --conf spark.yarn.submit.waitAppCompletion=true \
  --conf "spark.sql.hive.metastore.version=${HIVE_VERSION}" \
  --conf spark.sql.hive.metastore.jars=maven \
  --conf "spark.yarn.appMasterEnv.BRONZE_PATH=${BRONZE_PATH}" \
  --conf "spark.yarn.appMasterEnv.SILVER_DATABASE=${SILVER_DATABASE}" \
  --conf "spark.yarn.appMasterEnv.SILVER_TABLE=${SILVER_TABLE}" \
  /workspace/jobs/silver-transformation/main.py
