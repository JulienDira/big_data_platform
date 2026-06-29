#!/usr/bin/env bash
set -euo pipefail

if [[ ! -f /data/hdfs/namenode/current/VERSION ]]; then
  hdfs namenode -format -force -nonInteractive
fi

exec hdfs namenode

