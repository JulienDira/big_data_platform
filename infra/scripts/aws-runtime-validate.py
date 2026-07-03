from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen


GLUE_ARTIFACT_KEYS = (
    "jobs/raw-consumer/aws.py",
    "jobs/bronze-ingestion/aws.py",
    "jobs/silver-transformation/aws.py",
    "jobs/gold-indicators/aws.py",
    "python/jobs-utils.zip",
    "python/serving-registry.zip",
    "contracts/market-candle-v1.avsc",
    "sql/market_daily_summary.sql",
    "sql/market_indicators.sql",
    "sql/market_indicators_latest.sql",
    "sql/market_multitimeframe_signals.sql",
)


class CommandError(RuntimeError):
    pass


@dataclass
class CommandResult:
    stdout: str
    stderr: str
    returncode: int


class CommandRunner:
    def __init__(self, cwd: Path):
        self.cwd = cwd

    def run(
        self,
        args: list[str],
        *,
        allow_failure: bool = False,
        json_output: bool = False,
        text_output: bool = False,
    ) -> Any:
        completed = subprocess.run(
            args,
            cwd=self.cwd,
            text=True,
            capture_output=True,
            check=False,
        )
        if completed.returncode != 0 and not allow_failure:
            command = " ".join(args)
            raise CommandError(
                f"Command failed ({completed.returncode}): {command}\n"
                f"stdout: {completed.stdout}\nstderr: {completed.stderr}"
            )
        if json_output:
            return json.loads(completed.stdout or "{}")
        if text_output:
            return completed.stdout.strip()
        return CommandResult(
            stdout=completed.stdout,
            stderr=completed.stderr,
            returncode=completed.returncode,
        )


class RuntimeValidator:
    def __init__(
        self,
        *,
        repo_root: Path,
        artifact_version: str,
        evidence_path: Path,
        runner: CommandRunner,
        sleeper=time.sleep,
        http_get=None,
    ):
        self.repo_root = repo_root
        self.artifact_version = artifact_version
        self.evidence_path = evidence_path
        self.runner = runner
        self.sleep = sleeper
        self.http_get = http_get or self.default_http_get
        self.evidence: dict[str, Any] = {
            "phase": "Phase 10 - AWS automated deployment and runtime validation",
            "artifact_version": artifact_version,
            "checks": [],
            "cleanup": [],
        }
        self.core_outputs: dict[str, Any] = {}
        self.batch_outputs: dict[str, Any] = {}
        self.serving_outputs: dict[str, Any] = {}
        self.ecs_cluster_name: str | None = None
        self.ecs_service_name: str | None = None
        self.raw_streaming_job_name: str | None = None
        self.raw_streaming_run_id: str | None = None
        self.bronze_streaming_job_name: str | None = None
        self.bronze_streaming_run_id: str | None = None

    def record(self, name: str, status: str, details: dict[str, Any] | None = None) -> None:
        self.evidence["checks"].append(
            {
                "name": name,
                "status": status,
                "details": details or {},
            }
        )

    def record_cleanup(
        self, name: str, status: str, details: dict[str, Any] | None = None
    ) -> None:
        self.evidence["cleanup"].append(
            {
                "name": name,
                "status": status,
                "details": details or {},
            }
        )

    def run(self) -> None:
        self.evidence["started_at_epoch"] = int(time.time())
        status = "failed"
        error: Exception | None = None
        try:
            self.load_outputs()
            self.verify_immutable_artifacts()
            self.run_ingestion_window()
            self.run_lake_jobs()
            self.verify_lake_outputs()
            self.verify_athena_outputs()
            self.verify_projection_and_api()
            self.verify_observability()
            status = "succeeded"
        except Exception as exc:
            self.record("runtime_validation", "failed", {"error": str(exc)})
            error = exc
        finally:
            self.cleanup()
            self.write_evidence(status)
        if error is not None:
            raise error

    def load_outputs(self) -> None:
        self.core_outputs = self.terraform_outputs("core")
        self.batch_outputs = self.terraform_outputs("batch")
        self.serving_outputs = self.terraform_outputs("serving")
        self.ecs_cluster_name = self.required_output(self.core_outputs, "ecs_cluster_name")
        self.ecs_service_name = self.required_output(self.core_outputs, "ecs_service_name")
        lake_jobs = self.required_output(self.batch_outputs, "lake_ingestion_glue_job_names")
        self.raw_streaming_job_name = lake_jobs["raw_streaming"]
        self.bronze_streaming_job_name = lake_jobs["bronze_streaming"]
        self.record(
            "terraform_outputs",
            "ok",
            {"stacks": ["core", "batch", "serving"]},
        )

    def terraform_outputs(self, stack: str) -> dict[str, Any]:
        self.terraform_init(stack)
        raw_outputs = self.runner.run(
            ["terraform", f"-chdir=infra/aws/{stack}", "output", "-json"],
            json_output=True,
        )
        return {name: item["value"] for name, item in raw_outputs.items()}

    def terraform_init(self, stack: str) -> None:
        bucket = required_env("TF_STATE_BUCKET")
        prefix = os.getenv("TF_STATE_PREFIX", "big-data-platform/dev").strip("/")
        region = os.getenv("TF_STATE_REGION") or required_env("AWS_REGION")
        self.runner.run(
            [
                "terraform",
                f"-chdir=infra/aws/{stack}",
                "init",
                "-input=false",
                "-reconfigure",
                f"-backend-config=bucket={bucket}",
                f"-backend-config=key={prefix}/{stack}.tfstate",
                f"-backend-config=region={region}",
                "-backend-config=use_lockfile=true",
            ]
        )

    def verify_immutable_artifacts(self) -> None:
        repository_url = self.required_output(self.core_outputs, "ecr_repository_url")
        repository_name = repository_url.split("/", 1)[1]
        self.runner.run(
            [
                "aws",
                "ecr",
                "describe-images",
                "--repository-name",
                repository_name,
                "--image-ids",
                f"imageTag={self.artifact_version}",
            ],
            json_output=True,
        )

        artifact_bucket = self.required_output(
            self.batch_outputs, "glue_artifact_bucket_name"
        )
        artifact_prefix = self.required_output(
            self.batch_outputs, "glue_artifact_key_prefix"
        ).strip("/")
        for key in GLUE_ARTIFACT_KEYS:
            self.head_s3_object(artifact_bucket, f"{artifact_prefix}/{key}")
        self.head_s3_object(
            artifact_bucket,
            f"artifacts/lambda/{self.artifact_version}/aws-serving-api.zip",
        )
        self.record(
            "immutable_artifacts",
            "ok",
            {"ecr_repository": repository_name, "artifact_bucket": artifact_bucket},
        )

    def run_ingestion_window(self) -> None:
        raw_job = self.require_value(self.raw_streaming_job_name, "raw streaming job")
        self.raw_streaming_run_id = self.start_glue_job(raw_job)
        self.record(
            "raw_streaming_started",
            "ok",
            {"job_name": raw_job, "job_run_id": self.raw_streaming_run_id},
        )

        self.scale_ecs_producer(1)
        self.runner.run(
            [
                "aws",
                "ecs",
                "wait",
                "services-stable",
                "--cluster",
                self.require_value(self.ecs_cluster_name, "ecs cluster"),
                "--services",
                self.require_value(self.ecs_service_name, "ecs service"),
            ]
        )
        producer_seconds = int(os.getenv("RUNTIME_PRODUCER_SECONDS", "120"))
        self.sleep(producer_seconds)
        self.wait_for_s3_objects(self.required_output(self.batch_outputs, "raw_output_path"))

        bronze_job = self.require_value(
            self.bronze_streaming_job_name, "bronze streaming job"
        )
        self.bronze_streaming_run_id = self.start_glue_job(bronze_job)
        self.record(
            "bronze_streaming_started",
            "ok",
            {"job_name": bronze_job, "job_run_id": self.bronze_streaming_run_id},
        )

        bronze_seconds = int(os.getenv("RUNTIME_BRONZE_STREAMING_SECONDS", "60"))
        self.sleep(bronze_seconds)
        self.scale_ecs_producer(0)
        self.stop_bronze_streaming()
        self.stop_raw_streaming()
        self.wait_for_s3_objects(
            self.required_output(self.batch_outputs, "bronze_output_path")
        )
        self.record(
            "producer_kinesis_raw_bronze_window",
            "ok",
            {"producer_seconds": producer_seconds, "bronze_seconds": bronze_seconds},
        )

    def run_lake_jobs(self) -> None:
        lake_jobs = self.required_output(self.batch_outputs, "lake_ingestion_glue_job_names")
        for label in ("silver_batch",):
            job_name = lake_jobs[label]
            run_id = self.start_glue_job(job_name)
            self.wait_for_glue_job(job_name, run_id)
            self.record("glue_job", "ok", {"job_name": job_name, "job_run_id": run_id})

        gold_job = self.required_output(self.batch_outputs, "glue_job_name")
        gold_run_id = self.start_glue_job(gold_job)
        self.wait_for_glue_job(gold_job, gold_run_id)
        self.record(
            "glue_job",
            "ok",
            {"job_name": gold_job, "job_run_id": gold_run_id},
        )

    def verify_lake_outputs(self) -> None:
        output_names = (
            "raw_output_path",
            "bronze_output_path",
            "silver_input_path",
            "gold_output_path",
            "trading_gold_output_base_path",
        )
        for name in output_names:
            self.wait_for_s3_objects(self.required_output(self.batch_outputs, name))
        self.record("s3_lake_outputs", "ok", {"outputs": list(output_names)})

    def verify_athena_outputs(self) -> None:
        databases = self.required_output(self.batch_outputs, "glue_databases")
        trading_gold_database = databases["trading_gold"]
        workgroup = self.required_output(self.batch_outputs, "athena_workgroup_name")
        counts = {}
        for table in ("market_indicators", "market_indicators_latest"):
            counts[table] = self.athena_count(trading_gold_database, table, workgroup)
            if counts[table] <= 0:
                raise RuntimeError(f"Athena table {table} returned no rows")
        self.record("athena_counts", "ok", counts)

    def verify_projection_and_api(self) -> None:
        projected = self.invoke_projection_lambda()
        if projected <= 0:
            raise RuntimeError("Latest projection Lambda projected no rows")

        table_name = self.required_output(self.serving_outputs, "latest_metrics_table_name")
        table_count = self.dynamodb_count(table_name)
        if table_count <= 0:
            raise RuntimeError("DynamoDB latest metrics table is empty")

        self.invoke_api_health_lambda()
        self.assert_api_gateway_requires_auth()
        self.record(
            "projection_api",
            "ok",
            {"projected_items": projected, "dynamodb_count": table_count},
        )

    def verify_observability(self) -> None:
        alarm_names = self.required_output(self.serving_outputs, "cloudwatch_alarm_names")
        alarms_response = self.runner.run(
            ["aws", "cloudwatch", "describe-alarms", "--alarm-names", *alarm_names],
            json_output=True,
        )
        found_alarms = {
            item["AlarmName"]
            for item in alarms_response.get("MetricAlarms", [])
        } | {
            item["AlarmName"]
            for item in alarms_response.get("CompositeAlarms", [])
        }
        missing_alarms = sorted(set(alarm_names) - found_alarms)
        if missing_alarms:
            raise RuntimeError(f"Missing CloudWatch alarms: {missing_alarms}")
        account_id = self.runner.run(
            ["aws", "sts", "get-caller-identity", "--query", "Account", "--output", "text"],
            text_output=True,
        )
        self.runner.run(
            [
                "aws",
                "budgets",
                "describe-budget",
                "--account-id",
                account_id,
                "--budget-name",
                self.required_output(self.serving_outputs, "poc_budget_name"),
            ],
            json_output=True,
        )
        self.record(
            "observability",
            "ok",
            {"alarms": alarm_names, "budget": self.serving_outputs["poc_budget_name"]},
        )

    def cleanup(self) -> None:
        if self.ecs_cluster_name and self.ecs_service_name:
            result = self.runner.run(
                [
                    "aws",
                    "ecs",
                    "update-service",
                    "--cluster",
                    self.ecs_cluster_name,
                    "--service",
                    self.ecs_service_name,
                    "--desired-count",
                    "0",
                ],
                allow_failure=True,
            )
            self.record_cleanup(
                "ecs_desired_count_zero",
                "ok" if result.returncode == 0 else "failed",
                {"returncode": result.returncode},
            )

        if self.raw_streaming_job_name and self.raw_streaming_run_id:
            result = self.runner.run(
                [
                    "aws",
                    "glue",
                    "batch-stop-job-run",
                    "--job-name",
                    self.raw_streaming_job_name,
                    "--job-run-ids",
                    self.raw_streaming_run_id,
                ],
                allow_failure=True,
            )
            self.record_cleanup(
                "raw_streaming_stopped",
                "ok" if result.returncode == 0 else "failed",
                {"returncode": result.returncode},
            )

        if self.bronze_streaming_job_name and self.bronze_streaming_run_id:
            result = self.runner.run(
                [
                    "aws",
                    "glue",
                    "batch-stop-job-run",
                    "--job-name",
                    self.bronze_streaming_job_name,
                    "--job-run-ids",
                    self.bronze_streaming_run_id,
                ],
                allow_failure=True,
            )
            self.record_cleanup(
                "bronze_streaming_stopped",
                "ok" if result.returncode == 0 else "failed",
                {"returncode": result.returncode},
            )

    def write_evidence(self, status: str) -> None:
        self.evidence["status"] = status
        self.evidence["completed_at_epoch"] = int(time.time())
        self.evidence_path.parent.mkdir(parents=True, exist_ok=True)
        self.evidence_path.write_text(
            json.dumps(self.evidence, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def start_glue_job(self, job_name: str) -> str:
        return self.runner.run(
            [
                "aws",
                "glue",
                "start-job-run",
                "--job-name",
                job_name,
                "--query",
                "JobRunId",
                "--output",
                "text",
            ],
            text_output=True,
        )

    def wait_for_glue_job(self, job_name: str, run_id: str) -> None:
        timeout = int(os.getenv("RUNTIME_GLUE_TIMEOUT_SECONDS", "1800"))
        poll_seconds = int(os.getenv("RUNTIME_POLL_SECONDS", "20"))
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            state = self.runner.run(
                [
                    "aws",
                    "glue",
                    "get-job-run",
                    "--job-name",
                    job_name,
                    "--run-id",
                    run_id,
                    "--query",
                    "JobRun.JobRunState",
                    "--output",
                    "text",
                ],
                text_output=True,
            )
            if state == "SUCCEEDED":
                return
            if state in {"FAILED", "TIMEOUT", "ERROR", "EXPIRED", "STOPPED"}:
                raise RuntimeError(f"Glue job {job_name}/{run_id} ended as {state}")
            self.sleep(poll_seconds)
        raise TimeoutError(f"Glue job {job_name}/{run_id} did not finish in time")

    def stop_raw_streaming(self) -> None:
        if not self.raw_streaming_job_name or not self.raw_streaming_run_id:
            return
        self.runner.run(
            [
                "aws",
                "glue",
                "batch-stop-job-run",
                "--job-name",
                self.raw_streaming_job_name,
                "--job-run-ids",
                self.raw_streaming_run_id,
            ]
        )
        self.raw_streaming_run_id = None

    def stop_bronze_streaming(self) -> None:
        if not self.bronze_streaming_job_name or not self.bronze_streaming_run_id:
            return
        self.runner.run(
            [
                "aws",
                "glue",
                "batch-stop-job-run",
                "--job-name",
                self.bronze_streaming_job_name,
                "--job-run-ids",
                self.bronze_streaming_run_id,
            ]
        )
        self.bronze_streaming_run_id = None

    def scale_ecs_producer(self, desired_count: int) -> None:
        self.runner.run(
            [
                "aws",
                "ecs",
                "update-service",
                "--cluster",
                self.require_value(self.ecs_cluster_name, "ecs cluster"),
                "--service",
                self.require_value(self.ecs_service_name, "ecs service"),
                "--desired-count",
                str(desired_count),
            ],
            json_output=True,
        )

    def head_s3_object(self, bucket: str, key: str) -> None:
        self.runner.run(
            ["aws", "s3api", "head-object", "--bucket", bucket, "--key", key],
            json_output=True,
        )

    def wait_for_s3_objects(self, s3_uri: str) -> None:
        bucket, prefix = parse_s3_uri(s3_uri)
        timeout = int(os.getenv("RUNTIME_S3_TIMEOUT_SECONDS", "300"))
        poll_seconds = int(os.getenv("RUNTIME_POLL_SECONDS", "20"))
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            result = self.runner.run(
                [
                    "aws",
                    "s3api",
                    "list-objects-v2",
                    "--bucket",
                    bucket,
                    "--prefix",
                    prefix.rstrip("/") + "/",
                    "--max-keys",
                    "1",
                ],
                json_output=True,
            )
            if int(result.get("KeyCount", 0)) > 0:
                return
            self.sleep(poll_seconds)
        raise TimeoutError(f"No S3 objects found under {s3_uri}")

    def athena_count(self, database: str, table: str, workgroup: str) -> int:
        query = f'SELECT count(*) AS row_count FROM "{database}"."{table}"'
        started = self.runner.run(
            [
                "aws",
                "athena",
                "start-query-execution",
                "--query-string",
                query,
                "--query-execution-context",
                f"Database={database}",
                "--work-group",
                workgroup,
            ],
            json_output=True,
        )
        query_id = started["QueryExecutionId"]
        self.wait_for_athena_query(query_id)
        page = self.runner.run(
            [
                "aws",
                "athena",
                "get-query-results",
                "--query-execution-id",
                query_id,
            ],
            json_output=True,
        )
        rows = page.get("ResultSet", {}).get("Rows", [])
        value = rows[1]["Data"][0]["VarCharValue"] if len(rows) > 1 else "0"
        return int(value)

    def wait_for_athena_query(self, query_id: str) -> None:
        timeout = int(os.getenv("RUNTIME_ATHENA_TIMEOUT_SECONDS", "300"))
        poll_seconds = int(os.getenv("RUNTIME_POLL_SECONDS", "10"))
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            result = self.runner.run(
                [
                    "aws",
                    "athena",
                    "get-query-execution",
                    "--query-execution-id",
                    query_id,
                    "--query",
                    "QueryExecution.Status.State",
                    "--output",
                    "text",
                ],
                text_output=True,
            )
            if result == "SUCCEEDED":
                return
            if result in {"FAILED", "CANCELLED"}:
                raise RuntimeError(f"Athena query {query_id} ended as {result}")
            self.sleep(poll_seconds)
        raise TimeoutError(f"Athena query {query_id} did not finish in time")

    def invoke_projection_lambda(self) -> int:
        payload = self.invoke_lambda(
            self.required_output(self.serving_outputs, "latest_projection_lambda_name"),
            {},
        )
        return int(payload.get("projected_items", 0))

    def invoke_api_health_lambda(self) -> None:
        payload = self.invoke_lambda(
            self.required_output(self.serving_outputs, "api_lambda_name"),
            {
                "rawPath": "/health",
                "requestContext": {"http": {"method": "GET"}},
            },
        )
        if int(payload.get("statusCode", 0)) != 200:
            raise RuntimeError(f"API Lambda health returned {payload}")

    def invoke_lambda(self, function_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        with tempfile.NamedTemporaryFile(delete=False) as handle:
            response_path = Path(handle.name)
        try:
            metadata = self.runner.run(
                [
                    "aws",
                    "lambda",
                    "invoke",
                    "--function-name",
                    function_name,
                    "--payload",
                    json.dumps(payload),
                    "--cli-binary-format",
                    "raw-in-base64-out",
                    str(response_path),
                ],
                json_output=True,
            )
            if int(metadata.get("StatusCode", 0)) != 200:
                raise RuntimeError(f"Lambda {function_name} returned {metadata}")
            return json.loads(response_path.read_text(encoding="utf-8") or "{}")
        finally:
            response_path.unlink(missing_ok=True)

    def dynamodb_count(self, table_name: str) -> int:
        result = self.runner.run(
            [
                "aws",
                "dynamodb",
                "scan",
                "--table-name",
                table_name,
                "--select",
                "COUNT",
            ],
            json_output=True,
        )
        return int(result.get("Count", 0))

    def assert_api_gateway_requires_auth(self) -> None:
        endpoint = self.required_output(self.serving_outputs, "api_gateway_endpoint")
        status_code = self.http_get(f"{endpoint.rstrip('/')}/health")
        if status_code not in {401, 403}:
            raise RuntimeError(f"Unauthenticated API Gateway returned {status_code}")

    @staticmethod
    def default_http_get(url: str) -> int:
        request = Request(url, method="GET")
        try:
            with urlopen(request, timeout=20) as response:
                return int(response.status)
        except HTTPError as exc:
            return int(exc.code)

    @staticmethod
    def required_output(outputs: dict[str, Any], name: str) -> Any:
        if name not in outputs or outputs[name] in (None, ""):
            raise RuntimeError(f"Missing Terraform output: {name}")
        return outputs[name]

    @staticmethod
    def require_value(value: str | None, label: str) -> str:
        if not value:
            raise RuntimeError(f"Missing {label}")
        return value


def parse_s3_uri(uri: str) -> tuple[str, str]:
    if not uri.startswith("s3://"):
        raise ValueError(f"Expected S3 URI, got {uri}")
    bucket_and_key = uri[5:]
    bucket, _, key = bucket_and_key.partition("/")
    return bucket, key


def required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def default_repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run controlled AWS runtime validation for the dev/POC stack."
    )
    parser.add_argument(
        "--evidence-file",
        default="build/aws-runtime-evidence.json",
        help="JSON evidence file written after validation.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Write a dry-run evidence file without calling AWS or Terraform.",
    )
    args = parser.parse_args()

    repo_root = default_repo_root()
    artifact_version = os.getenv("ARTIFACT_VERSION") or os.getenv("GITHUB_SHA", "")
    if not artifact_version:
        raise RuntimeError("ARTIFACT_VERSION or GITHUB_SHA must be set")

    validator = RuntimeValidator(
        repo_root=repo_root,
        artifact_version=artifact_version,
        evidence_path=repo_root / args.evidence_file,
        runner=CommandRunner(repo_root),
    )
    if args.dry_run:
        validator.record("dry_run", "ok", {"message": "No AWS calls executed."})
        validator.write_evidence("dry_run")
        return
    validator.run()


if __name__ == "__main__":
    main()
