# Phase Handoff

Living handoff document for Codex agents. Read this file before starting a new
phase, then update it at the end of the phase.

## Current Context

The project is an on-premise Spark/YARN/HDFS/Hive/Airflow/PostgreSQL platform
that is being made portable to AWS progressively. The on-premise platform must
remain functional while AWS entry points are added phase by phase.

Current stable on-premise architecture:

```text
Binance REST -> Kafka/Schema Registry -> Raw HDFS -> Bronze HDFS
-> Silver Hive -> Gold Hive -> Serving PostgreSQL
```

Current prepared AWS architecture:

```text
Binance REST -> ECS/Fargate producer -> Kinesis Data Stream
-> Glue Streaming Raw S3 -> Glue batch Bronze S3 -> Glue batch Silver S3
-> Glue Spark Gold S3 -> trading_gold S3 -> Glue Data Catalog -> Athena
-> DynamoDB latest projection -> API Gateway/Lambda -> Cognito/Streamlit
```

PostgreSQL remains an on-premise Serving target only. RDS/PostgreSQL is not part
of the current AWS target.

No AWS account/credentials are currently available for runtime validation.
AWS checks must therefore be reported as static/local only unless a real AWS
account is used.

## Previous Proven Baseline

On-premise Silver -> Gold -> Serving runtime proof was already obtained before
the AWS phases:

- YARN applications `silver-market-candles`, `gold-market-indicators` and
  `serving-market-datamart` finished with `SUCCEEDED`.
- Hive/HDFS `gold.market_indicators` was validated with 1476 rows.
- PostgreSQL Serving tables were filled:
  - `market_indicators`: 1476 rows;
  - `market_indicators_latest`: 12 rows;
  - `market_multitimeframe_signals`: 300 rows;
  - `market_daily_summary`: 6 rows.
- Spark History event logs/API were checked for the three applications.

AWS preparation before this phase:

- `apps/binance-producer/aws.py` exists as the Kinesis producer entry point.
- `infra/aws/core` exists for Kinesis, ECR, ECS/Fargate, IAM and producer logs.
- `jobs/raw-consumer/aws.py`, `jobs/bronze-ingestion/aws.py` and
  `jobs/silver-transformation/aws.py` prepare Kinesis -> Raw/Bronze/Silver S3.
- `jobs/gold-indicators/aws.py` reads Silver Parquet from S3, writes Gold
  Parquet, then materializes `trading_gold.*` Parquet datasets.
- `infra/aws/batch` exists for S3, Glue jobs, Glue Catalog and Athena.
- `apps/aws-serving-api`, `apps/streamlit-dashboard` and `infra/aws/serving`
  prepare DynamoDB latest metrics, API Gateway/Lambda, Cognito, Streamlit
  Cloud wiring, alarms and Budget.

## Last Completed Phase

Phase: AWS CI/CD and artifact deployment implementation.

Goal: implement the reproducible AWS CI/CD preparation path required before
global AWS runtime validation: GitHub Actions OIDC, immutable producer image,
Glue artifacts, Lambda Zip/S3 package and Terraform inputs.

Status: completed as static/local implementation. No local `terraform apply`,
AWS CLI runtime check, real Glue job, ECS/Kinesis runtime, API deployment,
Cognito login, Streamlit Cloud deployment or Budget runtime check was run.

## Phase Scope

Required docs read:

- `AGENTS.md`;
- `cadrage.md`;
- `docs/phase-handoff.md`;
- `docs/phase-template.md`;
- `docs/aws-service-iam-decisions.md`;
- `docs/aws-phase-prompts.md`;
- `docs/aws-static-quality-audit.md`;
- `docs/aws-cicd-deployment-cadrage.md`;
- `docs/aws-core-portability-cadrage.md`;
- `docs/aws-lake-ingestion-cadrage.md`;
- `docs/aws-serving-observability-cadrage.md`.

Files inspected:

- `.github` state, which was absent before this phase;
- `infra/aws/core`, `infra/aws/batch` and `infra/aws/serving`;
- `apps/binance-producer`, `apps/aws-serving-api`, `jobs`, `infra/scripts` and
  `tests`;
- AWS phase docs and current handoff.

## Changes Completed

- Added `.github/workflows/aws-deploy.yml`:
  - `pull_request` validates only;
  - `push` to `main` and `workflow_dispatch` run the dev deployment
    preparation path;
  - AWS auth uses GitHub OIDC and `AWS_DEPLOY_ROLE_ARN`;
  - no long-lived AWS key path is present;
  - runtime remains stopped: core apply uses `ecs_service_desired_count=0`,
    no Glue jobs are started and projection schedule stays disabled.
- Added `infra/scripts/package-aws-artifacts.py`:
  - packages Raw/Bronze/Silver/Gold Glue scripts;
  - packages `jobs-utils.zip`, `serving-registry.zip`, SQL and Avro contract;
  - packages `apps/aws-serving-api` as `aws-serving-api.zip`;
  - writes the Lambda base64 SHA-256 hash for Terraform.
- Updated `infra/aws/core`:
  - empty S3 backend for CI;
  - ECR image tag immutability;
  - ECS desired count default changed to `0`.
- Updated `infra/aws/batch`:
  - empty S3 backend for CI;
  - optional `glue_artifact_bucket_name`;
  - `upload_glue_artifacts_from_workspace` keeps local-dev Terraform uploads
    but lets CI consume pre-published immutable artifacts;
  - Glue IAM can read artifacts from the selected artifact bucket.
- Updated `infra/aws/serving`:
  - empty S3 backend for CI;
  - optional `lambda_package_s3_bucket`, `lambda_package_s3_key` and
    `lambda_package_source_hash`;
  - local `archive_file` packaging remains the fallback when S3 package inputs
    are not provided.
- Added tests for packaging layout and workflow guardrails.
- Updated `docs/aws-cicd-deployment-cadrage.md`,
  `docs/aws-service-iam-decisions.md` and AWS module READMEs.

## Validation Completed

Static/local validation:

- `git status --short --untracked-files=all` was checked before changes and
  was clean.
- Direct `python -m unittest ...` failed because the WindowsApps Python
  launcher could not create the process; `py -3` was not installed.
- `terraform fmt -recursive infra\aws` was run, then
  `terraform fmt -check -recursive infra\aws` passed.
- First `terraform init -backend=false` attempt failed because sandboxed
  network access to `registry.terraform.io` was blocked.
- `terraform -chdir=infra\aws\core init -backend=false -input=false`,
  `terraform -chdir=infra\aws\batch init -backend=false -input=false` and
  `terraform -chdir=infra\aws\serving init -backend=false -input=false`
  succeeded after approved network access for provider initialization.
- `terraform -chdir=infra\aws\core validate` passed.
- `terraform -chdir=infra\aws\batch validate` passed.
- `terraform -chdir=infra\aws\serving validate` passed.
- First `powershell -ExecutionPolicy Bypass -File .\platform.ps1 test` failed
  on Docker access:
  `C:\Users\julie\.docker\config.json: Access is denied` and Docker pipe
  access denied.
- The same `platform.ps1 test` command succeeded after approved Docker access:
  40 tests OK, 1 skipped because local Spark lacks the `spark-avro` package.
- `rg -n "aws_db|aws_rds|postgres|postgresql" infra\aws -g "*.tf"` returned no
  match.
- `rg -n "AWS_ACCESS_KEY_ID|AWS_SECRET_ACCESS_KEY|aws-access-key-id|aws-secret-access-key|secrets\." .github\workflows\aws-deploy.yml`
  returned no match.
- `rg -n "start-job-run|update-service --desired-count|put-record|put-records|streamlit deploy" .github\workflows\aws-deploy.yml`
  returned no match.
- `git diff --check` passed.

Validation not run:

- `terraform plan`;
- local `terraform apply`;
- GitHub Actions execution;
- AWS CLI runtime checks;
- ECS, Kinesis, Glue, S3, Athena, DynamoDB, API Gateway, Lambda, Cognito,
  Streamlit Cloud, CloudWatch alarms or Budgets runtime checks;
- Streamlit Cloud deployment.

## Proof Obtained

- The repo now contains a concrete GitHub Actions deployment preparation path.
- CI/CD ownership is explicit: image and Zip/S3 artifacts are built and
  published outside Terraform with the commit SHA as immutable version.
- Terraform consumes artifact references and still owns durable infrastructure.
- Local Terraform validation passes for core, batch and serving.
- Package and workflow guardrails are protected by unit tests.
- RDS/PostgreSQL AWS remains absent from Terraform by static scan.

## Not Yet Proven

- GitHub Environment `dev` exists with required variables.
- GitHub OIDC provider and deploy role exist and are trusted correctly.
- Terraform remote state bucket and lock table exist.
- The workflow runs successfully on GitHub.
- AWS producer image exists in ECR.
- Glue and Lambda artifacts exist in S3.
- Terraform apply succeeds in the target AWS account.
- ECS service steady state.
- Kinesis record ingestion in AWS.
- Glue Streaming consumption from Kinesis.
- Raw/Bronze/Silver S3 outputs in AWS.
- Glue Gold execution and `trading_gold` outputs.
- Glue Data Catalog visibility in AWS.
- Athena query execution.
- DynamoDB latest table deployment and projection execution.
- API Gateway/Lambda deployment and endpoint behavior.
- Cognito Hosted UI login, groups and JWT authorizer behavior.
- Streamlit Cloud deployment and authentication flow.
- CloudWatch alarms, SNS notifications and AWS Budget visibility.
- Bronze invalid direct Avro rejection through Spark `from_avro` in a classpath
  where the `spark-avro` jar is available.

## Next Recommended Phase

Proceed to `Phase 9 prompt - AWS deployment preparation` in
`docs/aws-phase-prompts.md`.

Do not proceed to global AWS runtime validation yet. The next phase should
bootstrap or verify GitHub OIDC, Terraform remote state/locking and GitHub
Environment variables, then run the automated dev/POC deployment preparation
path without starting the full data runtime.

## Required Start Checklist for Next Agent

Before changing files or running deployment:

1. Read `AGENTS.md`.
2. Read `cadrage.md`.
3. Read this `docs/phase-handoff.md`.
4. Read `docs/phase-template.md`.
5. Read `docs/aws-service-iam-decisions.md`.
6. Read `docs/aws-phase-prompts.md`.
7. Read `docs/aws-cicd-deployment-cadrage.md`.
8. Inspect `.github/workflows/aws-deploy.yml`, `infra/aws/core`,
   `infra/aws/batch`, `infra/aws/serving` and `infra/scripts`.
9. Confirm GitHub Environment `dev` variables:
   `AWS_REGION`, `AWS_DEPLOY_ROLE_ARN`, `AWS_ARTIFACT_BUCKET`,
   `TF_STATE_BUCKET`, `TF_STATE_LOCK_TABLE`, `TF_STATE_REGION`, `VPC_ID`,
   `FARGATE_SUBNET_IDS`, `STREAMLIT_CALLBACK_URLS`,
   `STREAMLIT_LOGOUT_URLS` and `API_CORS_ALLOWED_ORIGINS`.
10. Keep runtime disabled by default: ECS desired count `0`, no Glue job runs,
    projection schedule disabled and no Streamlit Cloud deploy.
11. Do not mark AWS runtime validated unless actual AWS runtime surfaces were
    checked.

## Suggested Commit Message

```text
ci: add AWS artifact deployment workflow
```
