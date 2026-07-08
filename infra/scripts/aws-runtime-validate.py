from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import time
from typing import Any


STACKS = ("core", "batch", "serving", "orchestration")

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

MANUAL_RUNTIME_CHECKS = (
    "ECS producer stable and able to publish records to Kinesis.",
    "Raw Glue Streaming writes Kinesis envelopes to S3.",
    "Bronze Glue Streaming decodes Raw records and writes accepted/rejected S3 data.",
    "Silver and Gold Glue batch jobs finish successfully on a controlled dataset.",
    "Glue Catalog tables are visible and Athena queries return expected rows.",
    "Latest metrics projection writes items to DynamoDB.",
    "API Gateway and Lambda respond through the expected Cognito-protected path.",
    "CloudWatch logs, alarms and the POC Budget are visible in AWS.",
)


class CommandError(RuntimeError):
    pass


def run_command(
    args: list[str],
    *,
    cwd: Path,
    json_output: bool = False,
    text_output: bool = False,
) -> Any:
    completed = subprocess.run(
        args,
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        command = " ".join(args)
        raise CommandError(
            f"Command failed ({completed.returncode}): {command}\n"
            f"stdout: {completed.stdout}\nstderr: {completed.stderr}"
        )
    if json_output:
        return json.loads(completed.stdout or "{}")
    if text_output:
        return completed.stdout.strip()
    return completed.stdout


def required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def default_repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def terraform_init(repo_root: Path, stack: str) -> None:
    bucket = required_env("TF_STATE_BUCKET")
    prefix = os.getenv("TF_STATE_PREFIX", "big-data-platform/dev").strip("/")
    region = os.getenv("TF_STATE_REGION") or required_env("AWS_REGION")
    run_command(
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
        ],
        cwd=repo_root,
    )


def terraform_outputs(repo_root: Path, stack: str) -> dict[str, Any]:
    terraform_init(repo_root, stack)
    raw_outputs = run_command(
        ["terraform", f"-chdir=infra/aws/{stack}", "output", "-json"],
        cwd=repo_root,
        json_output=True,
    )
    return {name: item["value"] for name, item in raw_outputs.items()}


def output(outputs: dict[str, dict[str, Any]], stack: str, name: str) -> Any:
    try:
        value = outputs[stack][name]
    except KeyError as exc:
        raise RuntimeError(f"Missing Terraform output: {stack}.{name}") from exc
    if value in (None, ""):
        raise RuntimeError(f"Empty Terraform output: {stack}.{name}")
    return value


def check_artifacts(
    *,
    repo_root: Path,
    outputs: dict[str, dict[str, Any]],
    artifact_version: str,
) -> dict[str, Any]:
    repository_url = output(outputs, "core", "ecr_repository_url")
    repository_name = repository_url.split("/", 1)[1]
    run_command(
        [
            "aws",
            "ecr",
            "describe-images",
            "--repository-name",
            repository_name,
            "--image-ids",
            f"imageTag={artifact_version}",
        ],
        cwd=repo_root,
        json_output=True,
    )

    artifact_bucket = output(outputs, "batch", "glue_artifact_bucket_name")
    artifact_prefix = output(outputs, "batch", "glue_artifact_key_prefix").strip("/")
    artifact_keys = [f"{artifact_prefix}/{key}" for key in GLUE_ARTIFACT_KEYS]
    artifact_keys.append(f"artifacts/lambda/{artifact_version}/aws-serving-api.zip")
    for key in artifact_keys:
        run_command(
            ["aws", "s3api", "head-object", "--bucket", artifact_bucket, "--key", key],
            cwd=repo_root,
            json_output=True,
        )

    return {
        "ecr_repository": repository_name,
        "artifact_bucket": artifact_bucket,
        "artifact_count": len(artifact_keys),
    }


def build_summary(outputs: dict[str, dict[str, Any]]) -> dict[str, Any]:
    lake_jobs = output(outputs, "batch", "lake_ingestion_glue_job_names")
    return {
        "kinesis_stream_name": output(outputs, "core", "kinesis_stream_name"),
        "ecs_cluster_name": output(outputs, "core", "ecs_cluster_name"),
        "ecs_service_name": output(outputs, "core", "ecs_service_name"),
        "glue_jobs": {
            "raw_streaming": lake_jobs["raw_streaming"],
            "bronze_streaming": lake_jobs["bronze_streaming"],
            "silver_batch": lake_jobs["silver_batch"],
            "gold_batch": output(outputs, "batch", "gold_glue_job_name"),
        },
        "lake_paths": {
            "raw": output(outputs, "batch", "raw_output_path"),
            "bronze": output(outputs, "batch", "bronze_output_path"),
            "silver": output(outputs, "batch", "silver_input_path"),
            "gold": output(outputs, "batch", "gold_output_path"),
            "trading_gold": output(outputs, "batch", "trading_gold_output_base_path"),
        },
        "athena_workgroup_name": output(outputs, "batch", "athena_workgroup_name"),
        "latest_metrics_table_name": output(
            outputs, "serving", "latest_metrics_table_name"
        ),
        "api_lambda_name": output(outputs, "serving", "api_lambda_name"),
        "latest_projection_lambda_name": output(
            outputs, "serving", "latest_projection_lambda_name"
        ),
        "api_gateway_endpoint": output(outputs, "serving", "api_gateway_endpoint"),
        "batch_pipeline_state_machine_arn": output(
            outputs, "orchestration", "batch_pipeline_state_machine_arn"
        ),
        "batch_pipeline_schedule_name": output(
            outputs, "orchestration", "batch_pipeline_schedule_name"
        ),
        "batch_pipeline_schedule_enabled": output(
            outputs, "orchestration", "batch_pipeline_schedule_enabled"
        ),
    }


def write_evidence(evidence_path: Path, evidence: dict[str, Any]) -> None:
    evidence["completed_at_epoch"] = int(time.time())
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_path.write_text(
        json.dumps(evidence, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def deployment_summary(
    *,
    repo_root: Path,
    artifact_version: str,
    evidence_path: Path,
) -> None:
    evidence = {
        "phase": "AWS deployment summary",
        "artifact_version": artifact_version,
        "aws_runtime_proven": False,
        "checks": [],
        "manual_runtime_checks": list(MANUAL_RUNTIME_CHECKS),
        "started_at_epoch": int(time.time()),
    }
    status = "failed"
    try:
        outputs = {stack: terraform_outputs(repo_root, stack) for stack in STACKS}
        evidence["summary"] = build_summary(outputs)
        artifact_details = check_artifacts(
            repo_root=repo_root,
            outputs=outputs,
            artifact_version=artifact_version,
        )
        evidence["checks"] = [
            {"name": "terraform_outputs", "status": "ok", "details": {"stacks": STACKS}},
            {"name": "artifacts", "status": "ok", "details": artifact_details},
            {
                "name": "runtime",
                "status": "manual",
                "details": {"executed_by_this_script": False},
            },
        ]
        status = "succeeded"
    except Exception as exc:
        evidence["checks"].append(
            {"name": "deployment_summary", "status": "failed", "details": {"error": str(exc)}}
        )
        raise
    finally:
        evidence["status"] = status
        write_evidence(evidence_path, evidence)


def write_dry_run_evidence(evidence_path: Path, artifact_version: str) -> None:
    write_evidence(
        evidence_path,
        {
            "phase": "AWS deployment summary",
            "artifact_version": artifact_version,
            "aws_runtime_proven": False,
            "status": "dry_run",
            "checks": [
                {
                    "name": "dry_run",
                    "status": "ok",
                    "details": {"message": "No AWS or Terraform calls executed."},
                }
            ],
            "summary": {},
            "manual_runtime_checks": list(MANUAL_RUNTIME_CHECKS),
        },
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Write a short AWS deployment summary for the dev/POC stack."
    )
    parser.add_argument(
        "--evidence-file",
        default="build/aws-runtime-evidence.json",
        help="JSON summary file written after validation.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Write a dry-run summary file without calling AWS or Terraform.",
    )
    args = parser.parse_args()

    repo_root = default_repo_root()
    evidence_path = repo_root / args.evidence_file
    artifact_version = os.getenv("ARTIFACT_VERSION") or os.getenv("GITHUB_SHA", "")
    if args.dry_run:
        write_dry_run_evidence(evidence_path, artifact_version or "dry-run")
        return
    if not artifact_version:
        raise RuntimeError("ARTIFACT_VERSION or GITHUB_SHA must be set")

    deployment_summary(
        repo_root=repo_root,
        artifact_version=artifact_version,
        evidence_path=evidence_path,
    )


if __name__ == "__main__":
    main()
