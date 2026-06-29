#!/usr/bin/env bash
set -euo pipefail

: "${SPARK_VERSION:?}"
: "${KAFKA_BOOTSTRAP_SERVERS:?}"
: "${KAFKA_TOPIC:?}"
: "${RAW_PATH:?}"
: "${RAW_CHECKPOINT_PATH:?}"

APP_NAME="raw-consumer-market-candles"

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
  --conf "spark.yarn.appMasterEnv.KAFKA_TOPIC=${KAFKA_TOPIC}" \
  --conf "spark.yarn.appMasterEnv.RAW_PATH=${RAW_PATH}" \
  --conf "spark.yarn.appMasterEnv.RAW_CHECKPOINT_PATH=${RAW_CHECKPOINT_PATH}" \
  --py-files /workspace/jobs/raw-consumer/raw_config.py \
  /workspace/jobs/raw-consumer/main.py
