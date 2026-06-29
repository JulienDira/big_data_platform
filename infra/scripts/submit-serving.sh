#!/usr/bin/env bash
set -euo pipefail

: "${HIVE_VERSION:?}"
: "${GOLD_DATABASE:?}"
: "${GOLD_TABLE:?}"
: "${DATAMART_JDBC_URL:?}"
: "${DATAMART_DB_USER:?}"
: "${DATAMART_DB_PASSWORD:?}"
: "${DATAMART_INDICATORS_TABLE:?}"
: "${DATAMART_LATEST_TABLE:?}"
: "${DATAMART_MULTITIMEFRAME_TABLE:?}"
: "${DATAMART_DAILY_SUMMARY_TABLE:?}"
: "${DATAMART_BASE_INTERVAL:?}"
: "${DATAMART_CONTEXT_INTERVALS:?}"

UTILS_ZIP="/tmp/jobs-utils.zip"
python3 /workspace/infra/scripts/package-job-utils.py "${UTILS_ZIP}"

exec spark-submit \
  --master yarn \
  --deploy-mode cluster \
  --name serving-market-datamart \
  --py-files "${UTILS_ZIP},/workspace/jobs/serving-datamart/registry.py" \
  --files "/workspace/jobs/serving-datamart/sql/market_indicators.sql,/workspace/jobs/serving-datamart/sql/market_indicators_latest.sql,/workspace/jobs/serving-datamart/sql/market_multitimeframe_signals.sql,/workspace/jobs/serving-datamart/sql/market_daily_summary.sql" \
  --packages "org.postgresql:postgresql:42.7.4" \
  --conf spark.yarn.submit.waitAppCompletion=true \
  --conf "spark.sql.hive.metastore.version=${HIVE_VERSION}" \
  --conf spark.sql.hive.metastore.jars=maven \
  --conf "spark.yarn.appMasterEnv.GOLD_DATABASE=${GOLD_DATABASE}" \
  --conf "spark.yarn.appMasterEnv.GOLD_TABLE=${GOLD_TABLE}" \
  --conf "spark.yarn.appMasterEnv.DATAMART_JDBC_URL=${DATAMART_JDBC_URL}" \
  --conf "spark.yarn.appMasterEnv.DATAMART_DB_USER=${DATAMART_DB_USER}" \
  --conf "spark.yarn.appMasterEnv.DATAMART_DB_PASSWORD=${DATAMART_DB_PASSWORD}" \
  --conf "spark.yarn.appMasterEnv.DATAMART_INDICATORS_TABLE=${DATAMART_INDICATORS_TABLE}" \
  --conf "spark.yarn.appMasterEnv.DATAMART_LATEST_TABLE=${DATAMART_LATEST_TABLE}" \
  --conf "spark.yarn.appMasterEnv.DATAMART_MULTITIMEFRAME_TABLE=${DATAMART_MULTITIMEFRAME_TABLE}" \
  --conf "spark.yarn.appMasterEnv.DATAMART_DAILY_SUMMARY_TABLE=${DATAMART_DAILY_SUMMARY_TABLE}" \
  --conf "spark.yarn.appMasterEnv.DATAMART_BASE_INTERVAL=${DATAMART_BASE_INTERVAL}" \
  --conf "spark.yarn.appMasterEnv.DATAMART_CONTEXT_INTERVALS=${DATAMART_CONTEXT_INTERVALS}" \
  /workspace/jobs/serving-datamart/main.py
