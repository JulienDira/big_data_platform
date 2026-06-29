from __future__ import annotations

import pendulum
from airflow import DAG
from airflow.operators.bash import BashOperator


with DAG(
    dag_id="raw_market_candles",
    description="Submit the Raw market candles Spark streaming job on YARN.",
    start_date=pendulum.datetime(2026, 1, 1, tz="UTC"),
    schedule=None,
    catchup=False,
    max_active_runs=1,
    default_args={"owner": "big-data-platform", "retries": 0},
    tags=["big-data-platform", "streaming", "raw"],
) as dag:
    BashOperator(
        task_id="submit_raw_to_yarn",
        bash_command="bash /workspace/infra/scripts/submit-raw-consumer.sh ",
    )
