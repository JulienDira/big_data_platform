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

Phase: AWS Avro lake ingestion implementation.

Goal: implement the missing AWS path from Kinesis to S3 Raw/Bronze/Silver,
harmonize AWS Kinesis payloads on Avro binary instead of JSON, keep local
Kafka/Confluent Avro working, and update the documentation/phase sequence.

Status: implemented and prepared for static validation. No AWS runtime resource
was deployed or checked in a real AWS account.

## Start Diagnostic

Required docs read before changes:

- `AGENTS.md`;
- `cadrage.md`;
- `docs/phase-handoff.md`;
- `docs/phase-template.md`;
- `docs/aws-service-iam-decisions.md`;
- `docs/aws-phase-prompts.md`;
- `docs/aws-core-portability-cadrage.md`;
- `docs/aws-lake-ingestion-cadrage.md`.

Initial checks:

- `git status --short` showed existing documentation changes from the previous
  cadrage phase:
  - `docs/aws-service-iam-decisions.md`;
  - `docs/phase-handoff.md`;
  - untracked `docs/aws-lake-ingestion-cadrage.md`.
- Nothing was reverted.
- `rg` and direct reads covered the producer, Raw/Bronze/Silver jobs,
  `jobs/utils`, Terraform AWS modules and related tests.

## Changes Completed

Producer AWS:

- `apps/binance-producer/aws.py` now writes Avro binary Kinesis record data
  based on `contracts/market-candle/v1.avsc`.
- Kinesis partition key remains `symbol|interval`.
- `apps/binance-producer/avro_codec.py` was added for Avro encode/decode
  support, with `fastavro` support and a fixed-schema fallback for tests.
- `apps/binance-producer/requirements-aws.txt` now includes `fastavro`.

Shared jobs logic:

- Added `jobs/utils/bronze.py` for shared Avro decoding, Bronze valid output
  and Bronze rejected output.
- Added `jobs/utils/silver.py` and moved the pure `build_silver` logic there.
- Added `jobs/utils/aws_args.py` for simple Glue-style argument parsing.
- Updated local `jobs/bronze-ingestion/main.py` to use the shared Bronze Avro
  helper while preserving Confluent Avro header stripping.
- Updated local `jobs/silver-transformation/main.py` to import shared
  `build_silver`.

AWS lake entry points:

- Added `jobs/raw-consumer/aws.py`:
  - reads Avro records from Kinesis with Glue Streaming;
  - writes Raw Parquet envelope rows to S3;
  - preserves Kinesis metadata and `is_avro_decodable`;
  - partitions by `symbol`, `interval`, `ingestion_date`, `ingestion_hour`.
- Added `jobs/bronze-ingestion/aws.py`:
  - reads Raw S3;
  - decodes direct Avro binary payloads;
  - writes Bronze S3 and rejected Bronze S3.
- Added `jobs/silver-transformation/aws.py`:
  - reads Bronze S3;
  - applies shared Silver quality and deduplication rules;
  - writes Silver S3 for `jobs/gold-indicators/aws.py`.

Terraform AWS:

- Extended `infra/aws/batch` rather than creating a parallel stack.
- Added Raw, Bronze, rejected and checkpoint prefixes.
- Added Raw and Bronze Glue Catalog databases/tables.
- Added uploaded Glue scripts for Raw, Bronze and Silver.
- Added upload of `contracts/market-candle/v1.avsc` for Glue jobs.
- Added dedicated least-privilege roles:
  - `glue-raw-streaming-role`;
  - `glue-lake-transform-role`.
- Added Glue jobs:
  - Avro Kinesis -> Raw S3 streaming;
  - Raw S3 -> Bronze S3 batch;
  - Bronze S3 -> Silver S3 batch.
- Added outputs for lake paths and lake ingestion Glue job names.
- Did not add DynamoDB, Lambda, API Gateway, Streamlit, Budgets, RDS or AWS
  PostgreSQL resources.

Tests:

- Updated `tests/test_producer_aws.py` for Avro binary payloads.
- Updated `tests/test_utils_transforms.py` for Bronze rejected records and the
  shared Silver contract.
- Extended `tests/test_contract.py` forbidden AWS service scans.

Documentation:

- Updated `docs/aws-lake-ingestion-cadrage.md` from JSON to Avro binary.
- Updated `docs/aws-service-iam-decisions.md` with Avro Kinesis and deferred
  Glue Schema Registry full integration.
- Updated `docs/aws-core-portability-cadrage.md`, `docs/aws-phase-prompts.md`,
  `infra/aws/core/README.md`, `infra/aws/batch/README.md`, `jobs/README.md`
  and `cadrage.md`.

## Decisions Taken

- AWS Kinesis now targets Avro binary payloads based on the canonical
  `contracts/market-candle/v1.avsc` contract.
- Full AWS Glue Schema Registry integration is not implemented in this phase;
  it remains deferred because it would expand the producer/runtime scope.
- Raw storage remains Parquet on both local and AWS paths.
- Local Kafka keeps Confluent Avro framing; AWS Kinesis uses direct Avro binary
  payloads.
- Bronze owns decoding and first technical validity checks.
- Silver owns closed-candle filtering, OHLCV quality and deduplication.
- AWS runtime validation is still not the next step until the AWS path can be
  deployed in a real account.

## Validation Completed

Static and local validations completed:

```powershell
powershell -ExecutionPolicy Bypass -File .\platform.ps1 test
terraform fmt -check -recursive infra/aws
terraform -chdir=infra/aws/core validate
terraform -chdir=infra/aws/batch validate
rg -n "aws_db|aws_rds|postgres|postgresql" infra/aws -g "*.tf"
rg -n "aws_dynamodb|aws_lambda|aws_api_gateway|aws_apigateway|aws_budgets_budget" infra/aws -g "*.tf"
git diff --check
git status --short
```

- `platform.ps1 test`: passed, 23 tests OK. The first sandboxed attempt was
  blocked by local Docker pipe permissions, then the same command passed after
  running with the required Docker access.
- `terraform fmt -check -recursive infra/aws`: passed.
- `terraform -chdir=infra/aws/core validate`: passed.
- `terraform -chdir=infra/aws/batch validate`: passed.
- Forbidden Terraform resource scans returned no match for AWS PostgreSQL/RDS,
  DynamoDB, Lambda, API Gateway or Budgets.
- Stale JSON-related AWS wording scan returned no match for the replaced Avro
  payload decision.
- `git diff --check`: passed. Git reported CRLF normalization warnings only.

No `terraform plan`, `terraform apply`, AWS CLI deployment, Glue run or AWS
runtime check belongs to this phase.

## Proof Obtained

- The repo now contains static code and Terraform for Avro Kinesis -> Raw S3 ->
  Bronze S3 -> Silver S3.
- The AWS producer record test verifies Avro binary payloads and partition key
  behavior.
- Shared Silver logic is reusable by local and AWS entry points.
- Terraform now has dedicated lake ingestion IAM boundaries.

## Not Yet Proven

- AWS producer image has not been built or pushed to ECR.
- ECS service steady state is not proven.
- Kinesis record ingestion is not proven in AWS.
- Glue Streaming has not consumed Kinesis.
- Raw/Bronze/Silver S3 datasets have not been produced in AWS.
- Silver Parquet data in S3 was not verified by the Gold Glue job.
- Glue Gold job execution was not started.
- Gold and `trading_gold` S3 outputs were not verified.
- Glue Data Catalog tables were not verified in AWS.
- Athena query execution was not verified.
- CI/CD still does not build/push the producer image or publish immutable Glue
  artifacts.
- Full Glue Schema Registry integration remains unimplemented and uncadred.

## Next Recommended Phase

Recommended next phase: cadrage of the later AWS restitution/API/observability
scope.

Do not make AWS runtime validation the next phase yet. Runtime validation should
happen only after the selected AWS path has been implemented and a real AWS
account is available: producer/Kinesis/ECS, Kinesis -> S3 Raw/Bronze/Silver,
Glue Gold/trading_gold and any later API/dashboard/observability surfaces
explicitly included in scope.

Use the `Phase 5 prompt - Restitution, API and observability cadrage` section
in `docs/aws-phase-prompts.md`.

## Required Start Checklist for Next Agent

Before changing files, the next agent must:

1. Read `AGENTS.md`.
2. Read `cadrage.md`.
3. Read this `docs/phase-handoff.md`.
4. Read `docs/phase-template.md`.
5. Read `docs/aws-service-iam-decisions.md`.
6. Read `docs/aws-phase-prompts.md`.
7. Inspect the real repo with `git status --short`, `rg` and direct file reads.
8. Do not revert unrelated existing changes.
9. Distinguish implementation, static validation and real AWS runtime proof.

Do not mark a phase as runtime-validated unless the actual runtime surfaces were
checked.

## Suggested Commit Message

```text
feat: add AWS Avro lake ingestion path
```
