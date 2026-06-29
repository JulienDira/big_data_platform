from __future__ import annotations

import pendulum
from airflow import DAG
from airflow.operators.bash import BashOperator


with DAG(
    dag_id="market_streaming_submit",
    description="Submit Raw then Bronze Spark streaming jobs on YARN.",
    start_date=pendulum.datetime(2026, 1, 1, tz="UTC"),
    schedule=None,
    catchup=False,
    max_active_runs=1,
    default_args={"owner": "big-data-platform", "retries": 0},
    tags=["big-data-platform", "streaming", "pipeline"],
) as dag:
    raw = BashOperator(
        task_id="submit_raw_to_yarn",
        bash_command="bash /workspace/infra/scripts/submit-raw-consumer.sh ",
    )

    bronze = BashOperator(
        task_id="submit_bronze_to_yarn",
        bash_command="bash /workspace/infra/scripts/submit-bronze.sh ",
    )

    raw >> bronze
