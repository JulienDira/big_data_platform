#!/usr/bin/env bash
set -euo pipefail

: "${HIVE_VERSION:?}"
: "${SILVER_DATABASE:?}"
: "${SILVER_TABLE:?}"
: "${GOLD_DATABASE:?}"
: "${GOLD_TABLE:?}"

UTILS_ZIP="/tmp/jobs-utils.zip"
python3 /workspace/infra/scripts/package-job-utils.py "${UTILS_ZIP}"

exec spark-submit \
  --master yarn \
  --deploy-mode cluster \
  --name gold-market-indicators \
  --py-files "${UTILS_ZIP}" \
  --conf spark.yarn.submit.waitAppCompletion=true \
  --conf "spark.sql.hive.metastore.version=${HIVE_VERSION}" \
  --conf spark.sql.hive.metastore.jars=maven \
  --conf "spark.yarn.appMasterEnv.SILVER_DATABASE=${SILVER_DATABASE}" \
  --conf "spark.yarn.appMasterEnv.SILVER_TABLE=${SILVER_TABLE}" \
  --conf "spark.yarn.appMasterEnv.GOLD_DATABASE=${GOLD_DATABASE}" \
  --conf "spark.yarn.appMasterEnv.GOLD_TABLE=${GOLD_TABLE}" \
  /workspace/jobs/gold-indicators/main.py
