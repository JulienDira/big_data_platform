from __future__ import annotations

import pendulum
from airflow import DAG
from airflow.operators.bash import BashOperator


with DAG(
    dag_id="gold_market_indicators",
    description="Submit the Gold market indicators Spark batch job on YARN.",
    start_date=pendulum.datetime(2026, 1, 1, tz="UTC"),
    schedule=None,
    catchup=False,
    max_active_runs=1,
    default_args={"owner": "big-data-platform", "retries": 0},
    tags=["big-data-platform", "batch", "gold"],
) as dag:
    BashOperator(
        task_id="submit_gold_to_yarn",
        bash_command="bash /workspace/infra/scripts/submit-gold.sh ",
    )
