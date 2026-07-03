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
-> Glue Streaming Raw S3 -> EventBridge Scheduler / Step Functions
-> Glue Streaming Bronze S3 -> Glue batch Silver S3 -> Glue Spark Gold S3
-> trading_gold S3 -> Glue Data Catalog -> Athena
-> DynamoDB latest projection -> API Gateway/Lambda -> Cognito/Streamlit
```

PostgreSQL remains an on-premise Serving target only. RDS/PostgreSQL is not part
of the current AWS target.

No local AWS credentials are currently available for runtime validation:
`aws sts get-caller-identity` returns `Unable to locate credentials`. The
GitHub CLI is also unavailable locally: `gh` is not recognized as a command.
AWS checks must therefore be reported as static/local only unless a real AWS
account and GitHub environment are used.

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

- `apps/binance-producer/aws.py` exists as the Kinesis producer entry point and
  retries failed `PutRecords` entries with bounded attempts.
- `infra/aws/core` exists for Kinesis, ECR, ECS/Fargate, IAM and producer logs.
- `jobs/raw-consumer/aws.py`, `jobs/bronze-ingestion/aws.py` and
  `jobs/silver-transformation/aws.py` prepare Kinesis -> Raw/Bronze/Silver S3.
- `jobs/gold-indicators/aws.py` reads Silver Parquet from S3, writes Gold
  Parquet, then materializes `trading_gold.*` Parquet datasets.
- `infra/aws/batch` exists for S3, Glue jobs, Glue Catalog and Athena.
- `apps/aws-serving-api`, `apps/streamlit-dashboard` and `infra/aws/serving`
  prepare DynamoDB latest metrics, API Gateway/Lambda, Cognito, Streamlit
  Cloud wiring, alarms and Budget.
- `infra/aws/orchestration` prepares EventBridge Scheduler and Step Functions
  for the regular batch chain after Bronze. The schedule is disabled by
  default.

## Last Completed Phase

Phase: Phase 12 - AWS Raw to Bronze streaming refactor.

Goal: replace the AWS Bronze batch job with a Glue Streaming job that reads Raw
S3 continuously, writes Bronze S3 and rejected S3 with separate checkpoints,
and keeps Silver/Gold as bounded batch steps.

Status: completed as static/local implementation and documentation. AWS runtime
validation was not executed because this phase did not run real Glue, Kinesis,
S3, Step Functions or EventBridge resources.

## Changes Completed

- Refactored `jobs/bronze-ingestion/aws.py`:
  - reads Raw S3 as a streaming Parquet file source with explicit schema;
  - reuses the shared Avro decode and Bronze valid/rejected transformations;
  - writes Bronze and rejected Parquet streams with separate checkpoints;
  - removes batch `WRITE_MODE=overwrite` behavior.
- Added shared helpers:
  - `AWS_RAW_MARKET_CANDLES_SCHEMA` in `jobs/utils/market_schema.py`;
  - `write_parquet_stream` in `jobs/utils/s3_io.py`.
- Updated `infra/aws/batch`:
  - Bronze Glue job is now `gluestreaming`;
  - job name is `bronze-market-candles-streaming`;
  - Bronze checkpoint, rejected checkpoint, trigger, watermark and
    `maxFilesPerTrigger` are Terraform-driven;
  - lake-transform IAM can write Bronze checkpoints without gaining Gold,
    `trading_gold`, DynamoDB, API or PostgreSQL access;
  - `lake_ingestion_glue_job_names` now exposes `bronze_streaming`.
- Updated `infra/aws/orchestration` and `.github/workflows/aws-deploy.yml`:
  - Step Functions now starts at Silver and runs Silver -> Gold -> latest
    projection;
  - the orchestration stack no longer receives a Bronze Glue job variable;
  - the schedule stays disabled by default.
- Updated `infra/scripts/aws-runtime-validate.py`:
  - starts Raw streaming, waits for Raw S3 objects, starts Bronze streaming,
    then stops both streams;
  - runs only Silver and Gold as batch lake jobs;
  - cleanup scales ECS down and stops both streaming jobs when present.
- Added static tests for Bronze streaming, orchestration and runtime-validator
  behavior.
- Updated docs: `cadrage.md`, `jobs/README.md`,
  `docs/aws-service-iam-decisions.md`, `docs/aws-lake-ingestion-cadrage.md`,
  `docs/aws-implementation-step-audit.md`, `infra/aws/README.md`,
  `infra/aws/batch/README.md`, `infra/aws/orchestration/README.md`.

No on-premise entry point, RDS/PostgreSQL AWS target, DynamoDB/API/dashboard
logic, Gold calculation or `trading_gold` contract was changed.

## Validation Completed

Repository state and source control:

- `git status --short --untracked-files=all` was checked before changes and
  the worktree was clean.

Static/local validation:

- First `powershell -ExecutionPolicy Bypass -File .\platform.ps1 test` failed
  on Docker access:
  `C:\Users\julie\.docker\config.json: Access is denied` and Docker pipe
  access denied.
- After approved Docker access,
  `powershell -ExecutionPolicy Bypass -File .\platform.ps1 test` passed:
  61 tests OK, 1 skipped because the local Spark classpath lacks the
  `spark-avro` package.
- First `terraform fmt -check -recursive infra/aws` reported
  `infra/aws/batch/main.tf`.
- `terraform fmt -recursive infra/aws` formatted that Terraform file.
- `terraform fmt -check -recursive infra/aws` passed.
- `terraform -chdir=infra/aws/batch validate` passed.
- `terraform -chdir=infra/aws/orchestration validate` passed.
- `terraform -chdir=infra/aws/serving validate` passed.
- `git diff --check` passed with LF/CRLF normalization warnings on Windows.

Runtime and deployment availability checks:

- No AWS runtime checks, Terraform apply, Step Functions execution,
  EventBridge schedule activation, Glue run, ECS run, Kinesis write, S3 object
  check, Athena query or Lambda invocation were executed in this phase.

## Proof Obtained

- The repo now statically models Raw and Bronze as Glue Streaming jobs.
- Bronze streaming reads Raw S3, writes Bronze and rejected S3, and uses
  dedicated checkpoints.
- Step Functions no longer tries to run a long-running Bronze stream as a
  synchronous batch step.
- The planned batch chain is now Silver -> Gold -> latest projection.
- Local unit/static tests and Terraform validation pass.

## Not Yet Proven

- GitHub Environment `dev` exists with required variables.
- GitHub OIDC provider and scoped deploy role exist and trust the expected
  repository/environment subject.
- Terraform state bucket and S3 lockfile permissions exist.
- The workflow runs successfully on GitHub.
- AWS producer image exists in ECR.
- Glue and Lambda artifacts exist in S3.
- Terraform apply succeeds in the target AWS account.
- ECS service steady state and controlled scale-down.
- Kinesis record ingestion in AWS.
- Raw Glue Streaming consumption from Kinesis.
- Bronze Glue Streaming consumption from Raw S3.
- Raw/Bronze/Silver S3 outputs in AWS.
- Glue Gold execution and `trading_gold` outputs.
- Glue Data Catalog visibility in AWS.
- Athena query execution.
- DynamoDB latest table deployment and projection execution.
- API Gateway/Lambda deployment and endpoint behavior.
- Cognito Hosted UI login, groups and JWT authorizer behavior.
- Streamlit Cloud deployment and authentication flow.
- CloudWatch alarms, SNS notifications and AWS Budget visibility.
- `build/aws-runtime-evidence.json` from a real AWS runtime-validation run.
- EventBridge Scheduler actually triggering the Step Functions state machine.
- Step Functions executing Silver, Gold and latest projection in AWS.
- Safe enabling of `batch_pipeline_schedule_enabled=true` in a bounded POC
  runtime window.

## Next Recommended Phase

Perform the one-time GitHub/AWS bootstrap described in `infra/aws/README.md`,
then run the GitHub Actions workflow through a push to `main` or
`workflow_dispatch` with the orchestration schedule still disabled.

If bootstrap is complete and the workflow succeeds, run controlled AWS runtime
validation. The runtime proof should start Raw streaming, start Bronze
streaming after Raw S3 objects appear, run the producer in a bounded window,
stop both streams, run Silver and Gold batch jobs, then verify S3, Glue Catalog,
Athena, latest projection, API/auth and observability surfaces that are in
scope.

If the workflow or runtime validation fails, recommend one targeted remediation
phase named after the failing surface, for example OIDC trust, Terraform state,
ECR artifact publication, ECS/Kinesis, Glue Raw streaming, Glue Bronze
streaming, Glue Silver, Glue Gold, Athena, Step Functions/Scheduler, DynamoDB
projection or API Gateway/Cognito.

Ready-to-use next-agent prompt:

```text
Mission:
Run the deployed GitHub Actions path in a real AWS/GitHub environment after
completing the bootstrap in infra/aws/README.md, then validate the Raw and
Bronze Glue Streaming path plus the scheduled Silver -> Gold -> latest
projection batch chain in a controlled window.

Before doing anything, read AGENTS.md, cadrage.md, docs/phase-handoff.md,
infra/aws/README.md, infra/aws/batch/README.md, infra/aws/orchestration/README.md
and .github/workflows/aws-deploy.yml. Confirm GitHub Environment dev has
AWS_ACCOUNT_ID, AWS_DEPLOY_ROLE_ARN, AWS_REGION, AWS_ARTIFACT_BUCKET,
TF_STATE_BUCKET, TF_STATE_REGION, VPC_ID, FARGATE_SUBNET_IDS,
STREAMLIT_CALLBACK_URLS, STREAMLIT_LOGOUT_URLS and API_CORS_ALLOWED_ORIGINS.
Confirm the AWS OIDC provider, deploy role trust, state bucket and S3 lockfile
permissions exist.

Run the workflow from GitHub, not with local long-lived AWS keys. Keep
batch_pipeline_schedule_enabled=false for the normal deployment. Capture exact
evidence from the GitHub run, Terraform outputs and build/aws-runtime-evidence.json.
For runtime proof, start Raw streaming, prove Raw S3 objects, start Bronze
streaming, prove Bronze S3 objects, run Silver and Gold batch, then run latest
projection. Only enable the one-minute EventBridge schedule in a bounded POC
window after a manual Step Functions run proves Silver -> Gold -> projection.
Do not claim AWS runtime proof if any bootstrap, permission or service check is
missing.
```

## Suggested Commit Message

```text
feat: stream AWS bronze ingestion
```
