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

AWS core preparation before this phase:

- `apps/binance-producer/aws.py` existed as the Kinesis producer entry point.
- `infra/aws/core` existed for Kinesis, ECR, ECS/Fargate, IAM and producer logs.
- `jobs/gold-indicators/aws.py` existed and read Silver Parquet from S3, wrote
  analytical Gold Parquet, then materialized `trading_gold.*` Parquet datasets.
- `infra/aws/batch` existed for S3, Glue Data Catalog, Glue Spark and Athena.

## Last Completed Phase

Phase: AWS restitution, API, Cognito, Streamlit Cloud and observability
implementation.

Goal: implement the framed AWS serving/application/observability surface
statically and locally, without AWS runtime validation.

Status: completed as static/local implementation. No `terraform plan`,
`terraform apply`, AWS CLI runtime check or Streamlit Cloud deployment was run.

## Phase Scope

Required docs read:

- `AGENTS.md`;
- `cadrage.md`;
- `docs/phase-handoff.md`;
- `docs/phase-template.md`;
- `docs/aws-service-iam-decisions.md`;
- `docs/aws-phase-prompts.md`;
- `docs/aws-core-portability-cadrage.md`;
- `docs/aws-lake-ingestion-cadrage.md`;
- `docs/aws-serving-observability-cadrage.md`.

Files inspected:

- `jobs/gold-indicators/aws.py`;
- `jobs/utils/serving.py`;
- `jobs/serving-datamart/registry.py`;
- `jobs/serving-datamart/sql/market_indicators_latest.sql`;
- `infra/aws/core/`;
- `infra/aws/batch/`;
- `tests/test_contract.py`;
- current AWS documentation files under `docs/`.

## Changes Completed

- Added `apps/aws-serving-api`:
  - read-only API Lambda handler for `/health`, `/metrics/latest`,
    `/metrics/history`, `/signals` and `/daily-summary`;
  - dedicated latest metrics projection handler reading
    `trading_gold.market_indicators_latest` through Athena and writing only the
    DynamoDB latest cache;
  - shared local helpers for parameter validation, fixed Athena query building,
    DynamoDB item mapping and JSON response shaping.
- Added `apps/streamlit-dashboard`:
  - Streamlit Cloud POC app using Cognito Hosted UI with PKCE;
  - API Gateway calls only;
  - no AWS SDK imports and no direct DynamoDB/Athena/S3/Glue access.
- Added `infra/aws/serving`:
  - DynamoDB latest metrics table keyed by `symbol` and `interval`, with
    optional TTL on `expires_at_epoch`;
  - API Lambda, projection Lambda, API Gateway HTTP API and JWT authorizer;
  - Cognito User Pool, Hosted UI domain, Streamlit public app client and
    `viewer` / `admin` groups;
  - least-privilege IAM roles for API reads and projection writes;
  - CloudWatch log groups, minimal alarms, Glue failure event rule, optional
    SNS email subscription and 50 EUR AWS Budget.
- Updated `infra/aws/batch`:
  - enabled Athena workgroup CloudWatch metrics;
  - exposed `athena_results_bucket_name` for the serving module.
- Updated tests for the new API/projection/Streamlit boundaries.
- Updated `docs/aws-service-iam-decisions.md` statuses to `Prepare` for the
  implemented static serving/API/auth/observability surface.

## Validation Completed

Static/local validation:

- `git status --short` was checked before editing.
- `terraform -chdir=infra/aws/serving init -backend=false` succeeded after
  explicit network approval to download providers only.
- `terraform -chdir=infra/aws/serving validate` succeeded.
- `terraform -chdir=infra/aws/batch validate` succeeded.
- `terraform fmt -check -recursive infra/aws` succeeded.
- `powershell -ExecutionPolicy Bypass -File .\platform.ps1 test` succeeded:
  33 tests OK, 1 skipped because the local Spark classpath lacks
  `spark-avro`.
- `rg -n "aws_db|aws_rds|postgres|postgresql" infra/aws -g "*.tf"` returned no
  Terraform match.
- `rg -n "boto3|botocore|aioboto3|awswrangler|s3fs" apps/streamlit-dashboard`
  returned no match.
- `rg -n "SparkSession|pyspark|calculate_indicators|rolling|ewm"
  apps/aws-serving-api` returned no match.
- `git diff --check` succeeded. It printed only line-ending warnings for
  existing CRLF/LF normalization behavior.

Validation not run:

- `terraform plan`;
- `terraform apply`;
- AWS CLI runtime checks;
- ECS, Kinesis, Glue, S3, Athena, DynamoDB, API Gateway, Lambda, Cognito,
  Streamlit Cloud, CloudWatch alarms or Budgets runtime checks;
- Streamlit Cloud deployment.

## Proof Obtained

- Static Terraform now defines the AWS latest metrics cache, read API, Cognito
  authentication surface, alarms and Budget.
- API Lambda code is read-only for market data: DynamoDB latest reads and fixed
  Athena queries only.
- DynamoDB writes are isolated in a separate projection Lambda.
- Streamlit Cloud wiring uses Cognito and API Gateway only, with no direct AWS
  data-service imports.
- RDS/PostgreSQL AWS is still absent from Terraform.

## Not Yet Proven

- AWS producer image exists in ECR.
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
- CI/CD build/push and immutable artifact publication.
- Bronze invalid direct Avro rejection through Spark `from_avro` in a classpath
  where the `spark-avro` jar is available.

## Next Recommended Phase

Proceed to AWS runtime validation only if a real AWS account, credentials,
callback URLs, alert email and deployment permissions are available.

Use `Optional phase 7 prompt - AWS runtime validation` in
`docs/aws-phase-prompts.md`, and keep the runtime proof explicit per service.
If runtime access is still unavailable, the next useful non-runtime phase is
CI/CD/artifact hardening for ECR images, Glue artifacts and Lambda packages.

## Required Start Checklist for Next Agent

Before changing files, the next agent must:

1. Read `AGENTS.md`.
2. Read `cadrage.md`.
3. Read this `docs/phase-handoff.md`.
4. Read `docs/phase-template.md`.
5. Read `docs/aws-service-iam-decisions.md`.
6. Read `docs/aws-phase-prompts.md`.
7. Read `docs/aws-core-portability-cadrage.md`.
8. Read `docs/aws-lake-ingestion-cadrage.md`.
9. Read `docs/aws-serving-observability-cadrage.md`.
10. Inspect the real repo with `git status --short`, `rg` and direct file reads.
11. Do not revert unrelated existing changes.
12. Distinguish implementation, static validation and real AWS runtime proof.

Do not mark a phase as runtime-validated unless the actual runtime surfaces were
checked.

## Suggested Commit Message

```text
feat: add AWS serving API auth and observability
```
