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

Phase: AWS Avro codec cleanup with `fastavro`.

Goal: align the AWS producer Avro codec with maintained Avro tooling by using
`fastavro` as the only binary Avro implementation, remove the manual fallback,
and strengthen Avro error-path tests.

Status: completed. No AWS runtime resource was deployed or checked.

## Phase Scope

Required docs read:

- `AGENTS.md`;
- `cadrage.md`;
- `docs/phase-handoff.md`;
- `docs/phase-template.md`;
- `docs/aws-service-iam-decisions.md`;
- `docs/aws-phase-prompts.md`;
- `docs/aws-core-portability-cadrage.md`;
- `docs/aws-lake-ingestion-cadrage.md`.

Files inspected:

- `apps/binance-producer/aws.py`;
- `apps/binance-producer/avro_codec.py`;
- `apps/binance-producer/common.py`;
- `apps/binance-producer/Dockerfile`;
- `apps/binance-producer/requirements-aws.txt`;
- `contracts/market-candle/v1.avsc`;
- `jobs/raw-consumer/aws.py`;
- `jobs/bronze-ingestion/aws.py`;
- `jobs/silver-transformation/aws.py`;
- `jobs/gold-indicators/aws.py`;
- `jobs/utils/`;
- `infra/aws/core/`;
- `infra/aws/batch/`;
- `tests/`;
- AWS documentation files under `docs/`.

## Changes Completed

- Replaced `apps/binance-producer/avro_codec.py` with a strict wrapper around
  `fastavro.parse_schema`, `fastavro.schemaless_writer` and
  `fastavro.schemaless_reader`.
- Removed the manual Avro fallback encoder/decoder.
- Kept the public helper interface used by `apps/binance-producer/aws.py`:
  `load_schema`, `encode_record`, `decode_record`.
- Added `fastavro==1.9.7` to `infra/images/pyspark-requirements.txt` so the
  Docker `spark-client` test image can run producer AWS Avro tests.
- Added producer test coverage for invalid Avro payloads.
- Added a guarded Bronze invalid direct Avro test. It is skipped in the local
  Spark test classpath when the `spark-avro` jar is unavailable.
- Updated `docs/aws-static-quality-audit.md` with the follow-up result.

## Validation Completed

```powershell
docker compose --env-file config/versions.env --env-file config/defaults.env -f compose.yml build spark-client
git status --short
powershell -ExecutionPolicy Bypass -File .\platform.ps1 test
git diff --check
```

Results:

- First Docker build attempt was blocked by local Docker access.
- Docker build rerun with Docker access: `spark-client` rebuilt successfully
  with `fastavro==1.9.7`.
- First `platform.ps1 test` attempt was blocked by local Docker access.
- Same test command rerun with Docker access: passed, 25 tests OK with
  1 skipped test.
- The skipped test is the guarded Bronze invalid direct Avro payload test,
  because local Spark did not have the `spark-avro` jar in its classpath.
- `git diff --check`: passed; Git reported an LF/CRLF normalization warning
  for this handoff file.

Not run:

- `terraform plan`;
- `terraform apply`;
- AWS CLI calls;
- ECS, Kinesis, Glue or Athena runtime checks.
- Terraform validation was not rerun because this phase did not change
  Terraform files.

## Proof Obtained

- AWS producer Avro binary encoding now depends on `fastavro`, not a custom
  partial Avro implementation.
- Producer tests verify canonical Avro binary round-trip behavior and invalid
  payload failure.
- The local Spark unit suite still passes after adding `fastavro` to the
  `spark-client` image dependencies.

## Not Yet Proven

- AWS producer image exists in ECR.
- ECS service steady state.
- Kinesis record ingestion in AWS.
- Glue Streaming consumption from Kinesis.
- Raw/Bronze/Silver S3 outputs in AWS.
- Glue Gold execution and `trading_gold` outputs.
- Glue Data Catalog visibility in AWS.
- Athena query execution.
- CI/CD build/push and immutable Glue artifact publication.
- Bronze invalid direct Avro rejection through Spark `from_avro` in a classpath
  where the `spark-avro` jar is available.

## Next Recommended Phase

Proceed to cadrage only:
`Phase 5 prompt - Restitution, API and observability cadrage` in
`docs/aws-phase-prompts.md`.

Do not make AWS runtime validation the next phase yet.

## Required Start Checklist for Next Agent

Before changing files, the next agent must:

1. Read `AGENTS.md`.
2. Read `cadrage.md`.
3. Read this `docs/phase-handoff.md`.
4. Read `docs/phase-template.md`.
5. Read `docs/aws-service-iam-decisions.md`.
6. Read `docs/aws-phase-prompts.md`.
7. Read `docs/aws-static-quality-audit.md`.
8. Inspect the real repo with `git status --short`, `rg` and direct file reads.
9. Do not revert unrelated existing changes.
10. Distinguish implementation, static validation and real AWS runtime proof.

Do not mark a phase as runtime-validated unless the actual runtime surfaces were
checked.

## Suggested Commit Message

```text
refactor: use fastavro for AWS Avro codec
```
