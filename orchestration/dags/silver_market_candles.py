from __future__ import annotations

import pendulum
from airflow import DAG
from airflow.operators.bash import BashOperator


with DAG(
    dag_id="silver_market_candles",
    description="Submit the Silver market candles Spark batch job on YARN.",
    start_date=pendulum.datetime(2026, 1, 1, tz="UTC"),
    schedule=None,
    catchup=False,
    max_active_runs=1,
    default_args={"owner": "big-data-platform", "retries": 0},
    tags=["big-data-platform", "batch", "silver"],
) as dag:
    BashOperator(
        task_id="submit_silver_to_yarn",
        bash_command="bash /workspace/infra/scripts/submit-silver.sh ",
    )
