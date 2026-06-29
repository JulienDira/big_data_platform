#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "Usage: $0 <spark-application-name>" >&2
  exit 2
fi

app_name="$1"

mapfile -t app_ids < <(
  yarn application -list -appStates RUNNING,ACCEPTED 2>/dev/null \
    | awk -v name="${app_name}" 'NR > 2 && $2 == name {print $1}'
)

if [ "${#app_ids[@]}" -eq 0 ]; then
  echo "No RUNNING or ACCEPTED YARN application named ${app_name}."
  exit 0
fi

for app_id in "${app_ids[@]}"; do
  echo "Killing YARN application ${app_id} (${app_name})."
  yarn application -kill "${app_id}"
done
