from __future__ import annotations

import pendulum
from airflow import DAG
from airflow.operators.bash import BashOperator


with DAG(
    dag_id="bronze_market_candles",
    description="Submit the Bronze market candles Spark streaming job on YARN.",
    start_date=pendulum.datetime(2026, 1, 1, tz="UTC"),
    schedule=None,
    catchup=False,
    max_active_runs=1,
    default_args={"owner": "big-data-platform", "retries": 0},
    tags=["big-data-platform", "streaming", "bronze"],
) as dag:
    BashOperator(
        task_id="submit_bronze_to_yarn",
        bash_command="bash /workspace/infra/scripts/submit-bronze.sh ",
    )
