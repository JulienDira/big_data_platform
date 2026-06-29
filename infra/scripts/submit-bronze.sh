#!/usr/bin/env bash
set -euo pipefail

: "${SPARK_VERSION:?}"
: "${KAFKA_BOOTSTRAP_SERVERS:?}"
: "${KAFKA_ERROR_TOPIC:?}"
: "${RAW_PATH:?}"
: "${BRONZE_PATH:?}"
: "${BRONZE_CHECKPOINT_PATH:?}"
: "${BRONZE_TRIGGER_INTERVAL:?}"
: "${BRONZE_WATERMARK_DELAY:?}"

APP_NAME="bronze-market-candles"

if command -v yarn >/dev/null 2>&1 \
  && yarn application -list -appStates RUNNING,ACCEPTED 2>/dev/null \
    | awk 'NR > 2 {print $2}' \
    | grep -Fxq "${APP_NAME}"; then
  echo "Spark application ${APP_NAME} is already RUNNING or ACCEPTED on YARN; skipping submit."
  exit 0
fi

exec spark-submit \
  --master yarn \
  --deploy-mode cluster \
  --name "${APP_NAME}" \
  --packages \
    "org.apache.spark:spark-sql-kafka-0-10_2.12:${SPARK_VERSION},org.apache.spark:spark-avro_2.12:${SPARK_VERSION}" \
  --files /workspace/contracts/market-candle/v1.avsc#market-candle-v1.avsc \
  --conf spark.yarn.submit.waitAppCompletion=false \
  --conf spark.yarn.appMasterEnv.CONTRACT_PATH=market-candle-v1.avsc \
  --conf "spark.yarn.appMasterEnv.KAFKA_BOOTSTRAP_SERVERS=${KAFKA_BOOTSTRAP_SERVERS}" \
  --conf "spark.yarn.appMasterEnv.KAFKA_ERROR_TOPIC=${KAFKA_ERROR_TOPIC}" \
  --conf "spark.yarn.appMasterEnv.RAW_PATH=${RAW_PATH}" \
  --conf "spark.yarn.appMasterEnv.BRONZE_PATH=${BRONZE_PATH}" \
  --conf "spark.yarn.appMasterEnv.BRONZE_CHECKPOINT_PATH=${BRONZE_CHECKPOINT_PATH}" \
  --conf "spark.yarn.appMasterEnv.BRONZE_TRIGGER_INTERVAL=${BRONZE_TRIGGER_INTERVAL}" \
  --conf "spark.yarn.appMasterEnv.BRONZE_WATERMARK_DELAY=${BRONZE_WATERMARK_DELAY}" \
  /workspace/jobs/bronze-ingestion/main.py
