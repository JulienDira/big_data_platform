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

Phase: AWS CI/CD and automated deployment cadrage.

Goal: define the simple, reproducible AWS deployment path that must exist
before any global AWS runtime validation: producer image to ECR, Glue artifacts
to S3, Lambda package to S3, Terraform inputs, GitHub Actions OIDC and the split
between Terraform and CI/CD.

Status: completed as documentation/cadrage only. No `terraform plan`,
`terraform apply`, AWS CLI runtime check, real Glue job, ECS/Kinesis runtime,
API deployment, Cognito login, Streamlit Cloud deployment or Budget runtime
check was run.

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
- `docs/aws-serving-observability-cadrage.md`;
- `docs/aws-static-quality-audit.md`.
- `docs/aws-service-iam-decisions.md`.

Official references consulted:

- GitHub Actions OIDC for AWS;
- GitHub Actions environments and environment variables;
- HashiCorp Terraform automation guidance;
- Amazon ECR tag immutability and image scanning;
- AWS Lambda zip package and container image documentation.

Files inspected:

- `AGENTS.md`;
- `cadrage.md`;
- `docs/phase-handoff.md`;
- `docs/phase-template.md`;
- `docs/aws-phase-prompts.md`;
- `docs/aws-static-quality-audit.md`;
- `docs/aws-core-portability-cadrage.md`;
- `docs/aws-lake-ingestion-cadrage.md`;
- `docs/aws-serving-observability-cadrage.md`;
- `docs/aws-service-iam-decisions.md`;
- current AWS documentation and phase-order references found with `rg`.

## Changes Completed

- Added `docs/aws-cicd-deployment-cadrage.md`:
  - GitHub Actions on `ubuntu-latest` as the target CI surface;
  - AWS OIDC as the normal authentication path, not long-lived AWS keys;
  - one-time bootstrap for Terraform remote state, locking and the GitHub
    deploy role;
  - immutable commit-SHA artifact versioning for ECR, Glue artifacts and Lambda
    package;
  - Zip/S3 as the default Lambda packaging choice, with Lambda ECR documented
    only as a future alternative;
  - explicit non-goals: no Glue job runs, no ECS/Kinesis runtime proof, no
    Streamlit Cloud deploy and no global AWS runtime validation.
- Updated `cadrage.md` so CI/CD cadrage and CI/CD/deployment implementation sit
  between the static audit and global AWS runtime validation.
- Updated `AGENTS.md` with the stable rule that CI/CD/deployment preparation
  must happen after the static audit and before runtime validation.
- Updated `docs/aws-phase-prompts.md`:
  - Phase 8 now implements CI/CD and artifact deployment;
  - Phase 9 prepares AWS deployment through the automated path without running
    the full data runtime;
  - runtime validation is now optional Phase 10.
- Updated `docs/aws-static-quality-audit.md` and
  `docs/aws-service-iam-decisions.md` so runtime AWS is no longer recommended
  directly after static audit.
- Updated this handoff with the new next-agent prompt.

## Validation Completed

Static/local validation:

- `git status --short --untracked-files=all` was checked. The working tree was
  already dirty before this phase with modified documentation, code, Terraform
  and test files from the static audit phase. No existing change was reverted.
- `git diff --check` succeeded. It printed only LF/CRLF normalization warnings
  for modified files on Windows.
- `rg -n "[ \t]+$" docs/aws-cicd-deployment-cadrage.md` returned no match for
  the new untracked cadrage file.
- A scan over `docs`, `AGENTS.md` and `cadrage.md` found the expected CI/CD,
  GitHub Actions, OIDC, immutable artifact and Lambda packaging references.
- A scan for legacy direct-runtime recommendations found no remaining active
  recommendation to use runtime validation as the next phase after the static
  audit.
- `rg -n "aws_db|aws_rds|postgres|postgresql" infra/aws -g "*.tf"` returned no
  match.

Validation not run:

- `platform.ps1 test`, because this phase changed documentation only;
- `terraform fmt` / `terraform validate`, because no Terraform files were
  changed in this phase;
- `terraform plan`;
- `terraform apply`;
- AWS CLI runtime checks;
- ECS, Kinesis, Glue, S3, Athena, DynamoDB, API Gateway, Lambda, Cognito,
  Streamlit Cloud, CloudWatch alarms or Budgets runtime checks;
- Streamlit Cloud deployment.

## Proof Obtained

- The documentation now makes CI/CD and automated deployment preparation a
  required phase before global AWS runtime validation.
- The deployment target is framed as GitHub Actions + AWS OIDC + immutable
  ECR/S3 artifacts + Terraform inputs.
- Lambda packaging is framed as Zip/S3 by default for the current lightweight
  Python API/projection code; Lambda ECR remains a later explicit alternative.
- Runtime proof boundaries remain explicit: no AWS service behavior was claimed
  from this docs-only phase.
- RDS/PostgreSQL AWS is still absent from Terraform by static scan.

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
- GitHub OIDC deploy role and Terraform remote state/locking bootstrap.
- GitHub Actions workflow on push to `main`.
- CI-published Lambda Zip/S3 package consumed by Terraform.
- Bronze invalid direct Avro rejection through Spark `from_avro` in a classpath
  where the `spark-avro` jar is available.

## Next Recommended Phase

Proceed to `Phase 8 prompt - AWS CI/CD and artifact deployment implementation`
in `docs/aws-phase-prompts.md`.

Do not proceed to global AWS runtime validation yet. Runtime validation is now
optional Phase 10 and should happen only after CI/CD publishes immutable
artifacts and the automated dev/POC deployment preparation path is reproducible.

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
10. Read `docs/aws-static-quality-audit.md`.
11. Read `docs/aws-cicd-deployment-cadrage.md`.
12. Inspect the real repo with `git status --short`, `rg` and direct file
    reads.
13. Do not revert unrelated existing changes.
14. Distinguish implementation, artifact publication, deployment preparation
    and real AWS runtime proof.

Do not mark a phase as runtime-validated unless the actual runtime surfaces were
checked.

## Suggested Commit Message

```text
docs: frame AWS CI deployment phase
```
