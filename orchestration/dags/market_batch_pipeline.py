from __future__ import annotations

import pendulum
from airflow import DAG
from airflow.operators.bash import BashOperator


with DAG(
    dag_id="market_batch_pipeline",
    description="Run the complete batch pipeline: Silver, Gold then Serving.",
    start_date=pendulum.datetime(2026, 1, 1, tz="UTC"),
    schedule=None,
    catchup=False,
    max_active_runs=1,
    default_args={"owner": "big-data-platform", "retries": 0},
    tags=["big-data-platform", "batch", "pipeline"],
) as dag:
    silver = BashOperator(
        task_id="submit_silver_to_yarn",
        bash_command="bash /workspace/infra/scripts/submit-silver.sh ",
    )

    gold = BashOperator(
        task_id="submit_gold_to_yarn",
        bash_command="bash /workspace/infra/scripts/submit-gold.sh ",
    )

    serving = BashOperator(
        task_id="submit_serving_to_yarn",
        bash_command="bash /workspace/infra/scripts/submit-serving.sh ",
    )

    silver >> gold >> serving
