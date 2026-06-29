#!/usr/bin/env bash
set -euo pipefail

until hdfs dfsadmin -safemode get >/dev/null 2>&1; do
  sleep 2
done

hdfs dfsadmin -safemode wait
hdfs dfs -mkdir -p \
  /data/raw/binance/market_candles \
  /data/bronze/market_candles \
  /checkpoints/raw/binance/market_candles \
  /checkpoints/bronze/market_candles \
  /spark-history \
  /tmp \
  /user/hive/warehouse \
  /warehouse/tablespace/managed/hive
hdfs dfs -chmod -R 1777 /tmp /spark-history
hdfs dfs -chmod -R 777 /data /checkpoints /user/hive /warehouse
