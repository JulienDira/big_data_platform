# Phase Handoff

Living handoff document for Codex agents. Read this file before starting a new
phase, then update it at the end of the phase.

## Current Context

The project is an on-premise Spark/YARN/HDFS/Hive/Airflow/PostgreSQL platform
that is being made portable to AWS progressively. The on-premise platform must
remain functional while AWS entry points are added phase by phase.

Permanent rules live in `AGENTS.md`. The target architecture and migration
cadrage live in `cadrage.md`. AWS service/IAM decisions live in
`docs/aws-service-iam-decisions.md`. AWS phase prompts live in
`docs/aws-phase-prompts.md`.

Current stable on-premise architecture:

```text
Binance REST -> Kafka/Schema Registry -> Raw HDFS -> Bronze HDFS
-> Silver Hive -> Gold Hive -> Serving PostgreSQL
```

Current prepared AWS core architecture:

```text
Binance REST -> ECS/Fargate producer -> Kinesis Data Stream
Kinesis -> S3 Raw/Bronze/Silver is not designed yet
Silver S3 -> Glue Spark -> Gold S3 -> trading_gold S3
-> Glue Data Catalog -> Athena
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

AWS batch preparation before this phase:

- `jobs/gold-indicators/aws.py` exists and reads Silver Parquet from S3, writes
  analytical Gold Parquet, then materializes `trading_gold.*` Parquet datasets.
- `infra/aws/batch` exists for S3, Glue Data Catalog, Glue Spark and Athena.
- AWS runtime proof for S3/Glue/Athena is still missing.

## Last Completed Phase

Phase: AWS core implementation.

Goal: implement the core AWS portability path defined in
`docs/aws-core-portability-cadrage.md`: producer to Kinesis, ECR/ECS/Fargate
packaging, Glue artifact packaging hardening, static/local validation and
handoff documentation.

Status: implemented and statically validated. No AWS runtime resource was
deployed or checked in a real AWS account.

## Start Diagnostic

Required docs read before changes:

- `AGENTS.md`;
- `cadrage.md`;
- `docs/phase-handoff.md`;
- `docs/phase-template.md`;
- `docs/aws-service-iam-decisions.md`;
- `docs/aws-phase-prompts.md`;
- `docs/aws-core-portability-cadrage.md`.

Initial checks:

- `git status --short` showed an existing dirty working tree with modified and
  untracked files from previous phases; nothing was reverted.
- Direct repo inspection covered:
  - `apps/binance-producer/main.py`;
  - `apps/binance-producer/model.py`;
  - `apps/binance-producer/Dockerfile`;
  - `apps/binance-producer/requirements.txt`;
  - `contracts/market-candle/v1.avsc`;
  - `tests/test_producer_model.py`;
  - `tests/test_contract.py`;
  - `jobs/gold-indicators/aws.py`;
  - `jobs/utils`;
  - `jobs/serving-datamart/registry.py`;
  - `jobs/serving-datamart/sql`;
  - `infra/aws/batch`;
  - current repo scripts and test entry points.

## Changes Completed

Producer AWS core:

- Added `apps/binance-producer/common.py` with shared producer runtime helpers:
  required env loading, CSV env parsing, positive integer env parsing, Binance
  latest candle fetch and `symbol|interval` partition key construction.
- Updated `apps/binance-producer/main.py` to reuse the shared helpers while
  keeping the Kafka/Schema Registry on-premise path in `main.py`.
- Added `apps/binance-producer/aws.py` as the AWS Kinesis entry point:
  - reads `AWS_REGION`, `KINESIS_STREAM_NAME`,
    `KINESIS_PUBLISH_BATCH_SIZE`, `MARKET_SYMBOLS`,
    `MARKET_INTERVALS`, `BINANCE_BASE_URL`, `PRODUCER_POLL_SECONDS`;
  - reuses the shared Binance fetch and `normalize_kline` path;
  - publishes canonical UTF-8 JSON records to Kinesis;
  - uses partition key `symbol|interval`;
  - batches records with Kinesis `put_records`.
- Added `apps/binance-producer/requirements-aws.txt` for `boto3`.
- Updated `apps/binance-producer/Dockerfile` with build arg
  `INSTALL_AWS_DEPS=true` for AWS images, leaving the default on-prem image
  path unchanged.

Tests:

- Added `tests/test_producer_aws.py` for Kinesis payload shape, partition key
  and batching.
- Updated `tests/test_contract.py` so the no-RDS contract checks Terraform AWS
  resources instead of rejecting the word `RDS` when documentation mentions it
  as an excluded service.

Terraform AWS core:

- Added `infra/aws/core`:
  - Kinesis Data Stream;
  - ECR repository;
  - ECS cluster;
  - ECS Fargate task definition and service;
  - ECS task role scoped to Kinesis writes;
  - ECS task execution role scoped to ECR image pull and producer logs;
  - CloudWatch log group;
  - outbound-only security group and Fargate subnet wiring variables.
- Added `infra/aws/core/README.md` with manual build/tag/push commands and
  runtime proof boundaries.

Glue/Spark packaging:

- Updated `infra/aws/batch` so Glue script, Python zips and SQL files use a
  versioned artifact key prefix:
  `glue_artifacts_prefix/glue_artifact_version`.
- Added `glue_artifact_key_prefix` output.
- Updated `infra/aws/batch/README.md` to document local-dev artifacts and the
  future CI/CD responsibility.

Documentation:

- Updated `docs/aws-service-iam-decisions.md` to mark Kinesis, ECS/Fargate,
  ECR/IAM and producer logs as prepared, with AWS runtime proof still missing.
- Updated this `docs/phase-handoff.md`.

## Key Files

- `apps/binance-producer/aws.py`: AWS Kinesis producer entry point.
- `apps/binance-producer/common.py`: shared producer helpers used by Kafka and
  Kinesis paths.
- `apps/binance-producer/Dockerfile`: optional AWS dependency install through
  `INSTALL_AWS_DEPS=true`.
- `tests/test_producer_aws.py`: Kinesis payload and partition-key tests.
- `infra/aws/core`: producer Kinesis/ECR/ECS/Fargate/IAM/logs stack.
- `infra/aws/batch`: Glue artifact packaging with explicit version segment.
- `docs/aws-service-iam-decisions.md`: current AWS service/IAM status.

## Validation Completed

Python unit test attempt on the Windows host:

```powershell
python -m unittest tests.test_producer_aws tests.test_producer_model tests.test_contract -v
```

Result: failed before running tests because the WindowsApps Python launcher
could not create the Python process.

```powershell
py -3 -m unittest tests.test_producer_aws tests.test_producer_model tests.test_contract -v
```

Result: failed before running tests because `py` is not installed or not on
`PATH`.

Terraform formatting:

```powershell
terraform fmt -recursive infra/aws
```

Result: exit 0; formatted `infra\aws\core\main.tf`.

```powershell
terraform fmt -check -recursive infra/aws
```

Result: exit 0.

Terraform initialization:

```powershell
terraform -chdir=infra/aws/core init -backend=false
```

Result: exit 0 after network approval; installed `hashicorp/aws v5.100.0` and
created `infra/aws/core/.terraform.lock.hcl`.

```powershell
terraform -chdir=infra/aws/batch init -backend=false
```

Result: exit 0 after network approval; reused `hashicorp/archive v2.8.0` and
`hashicorp/aws v5.100.0`.

Terraform validation:

```powershell
terraform -chdir=infra/aws/core validate
terraform -chdir=infra/aws/batch validate
```

Result: both returned `Success! The configuration is valid.`

Forbidden AWS Terraform scans:

```powershell
rg -n "aws_db|aws_rds|postgres|postgresql" infra/aws -g "*.tf"
rg -n "aws_dynamodb|aws_lambda|aws_api_gateway|aws_apigateway|aws_budgets_budget" infra/aws -g "*.tf"
```

Result: no matches for either scan.

Repo validation:

```powershell
powershell -ExecutionPolicy Bypass -File .\platform.ps1 test
```

Result:

- first sandboxed run failed on Docker access:
  `open C:\Users\julie\.docker\config.json: Access is denied` and
  `open //./pipe/docker_engine: Access is denied`;
- rerun with approved elevated Docker access passed:
  `Ran 21 tests in 39.433s` and `OK`;
- the run printed a non-blocking orphan-container warning for
  `big-data-platform-raw-consumer-market-candles-1`.

AWS runtime:

- `terraform plan` was not run because AWS credentials/account access are not
  available in this environment.
- No AWS runtime validation was claimed.

## Proof Obtained

- Kafka/on-prem producer entry point remains `apps/binance-producer/main.py`.
- AWS producer entry point exists at `apps/binance-producer/aws.py`.
- AWS producer records use canonical JSON matching
  `contracts/market-candle/v1.avsc`.
- Kinesis partition key is `symbol|interval`.
- Kinesis batching is unit-tested.
- `infra/aws/core` statically validates for Kinesis, ECR, ECS/Fargate, IAM and
  logs.
- `infra/aws/batch` still statically validates after versioned Glue artifact
  key hardening.
- Static scans found no AWS RDS/PostgreSQL resources and no DynamoDB, Lambda,
  API Gateway or Budgets Terraform resources.
- The repo unit/static test surface passes in the Docker Spark client.

## Not Yet Proven

- AWS producer image has not been built locally with `INSTALL_AWS_DEPS=true`.
- Producer image has not been pushed to ECR.
- `terraform plan` and `terraform apply` are not proven.
- ECS service steady state is not proven.
- CloudWatch producer logs are not proven.
- Kinesis record ingestion is not proven in AWS.
- The Kinesis -> S3 Raw/Bronze/Silver AWS ingestion path is still not
  implemented.
- Silver Parquet data in S3 was not verified.
- Glue job execution was not started.
- S3 Gold/trading_gold Parquet outputs were not verified.
- Glue Data Catalog tables were not verified in AWS.
- Athena query execution was not verified.
- CI/CD still does not build/push the producer image or publish immutable Glue
  artifacts.

## Next Recommended Phase

Recommended next phase: cadrage of the missing Kinesis -> S3 Raw/Bronze/Silver
lake ingestion path.

Do not make AWS runtime validation the next phase, even if credentials become
available. Runtime validation should happen only after the selected AWS path has
been framed and implemented: producer/Kinesis/ECS, Kinesis -> S3
Raw/Bronze/Silver, Glue Gold/trading_gold and any later API/dashboard/
observability surfaces explicitly included in scope.

Use the `Phase 3 prompt - Kinesis to S3 Raw/Bronze/Silver cadrage` section in
`docs/aws-phase-prompts.md`.

Suggested cadrage scope:

1. Audit on-prem `jobs/raw-consumer`, `jobs/bronze-ingestion`,
   `jobs/silver-transformation`, shared schemas and quality helpers.
2. Define the AWS Raw S3 contract from Kinesis: envelope, metadata,
   partitions, checkpointing and decode/error status.
3. Define Bronze decoding and technical validation on S3.
4. Define Silver typed/deduplicated closed candles on S3, compatible with
   `jobs/gold-indicators/aws.py`.
5. Decide Glue Streaming ETL or another justified processing pattern, with IAM,
   S3 prefixes, logs, costs and static tests.
6. Produce the implementation prompt for that lake ingestion path.

Do not implement in the next phase unless explicitly recadred:

- DynamoDB latest metrics;
- API Gateway/Lambda API;
- Streamlit/local dashboard support;
- advanced CloudWatch alarms;
- AWS Budgets;
- AWS PostgreSQL/RDS.

## Required Start Checklist for Next Agent

Before changing files, the next agent must:

1. Read `AGENTS.md`.
2. Read `cadrage.md`.
3. Read this `docs/phase-handoff.md`.
4. Read `docs/phase-template.md`.
5. Read `docs/aws-service-iam-decisions.md`.
6. Inspect the real repo with `git status --short`, `rg` and direct file reads.
7. Do not revert unrelated existing changes.
8. Distinguish implementation, static validation and real AWS runtime proof.

Do not mark a phase as runtime-validated unless the actual runtime surfaces were
checked.
