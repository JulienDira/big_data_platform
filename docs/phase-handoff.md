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
-> Glue batch Bronze S3 -> Glue batch Silver S3 -> Glue Spark Gold S3
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
  for the regular batch chain after Raw. The schedule is disabled by default.

## Last Completed Phase

Phase: Phase 11 - AWS scheduled batch orchestration.

Goal: add a Terraform-managed AWS orchestration layer that can trigger the
post-Raw batch chain every minute through EventBridge Scheduler and Step
Functions, while keeping the schedule disabled until controlled AWS runtime
validation is available.

Status: completed as static/local implementation and documentation. AWS runtime
validation was not executed because this phase stayed static/local and the repo
still lacks proven AWS/GitHub runtime execution.

## Changes Completed

- Added `infra/aws/orchestration`:
  - Step Functions Standard state machine for Bronze -> Silver -> Gold ->
    latest projection;
  - EventBridge Scheduler trigger with default expression `rate(1 minute)`;
  - schedule disabled by default through `batch_pipeline_schedule_enabled`;
  - DynamoDB `batch-pipeline` single-flight lock with conditional `PutItem`
    and TTL;
  - IAM roles for Step Functions and Scheduler;
  - CloudWatch log group and stack outputs.
- Extended `infra/aws/batch` outputs with scalar Bronze, Silver and Gold Glue
  job names for downstream Terraform wiring.
- Extended `infra/aws/serving` outputs with `latest_projection_lambda_arn`.
- Updated `.github/workflows/aws-deploy.yml`:
  - PR/static validation now includes `infra/aws/orchestration`;
  - non-PR Terraform apply now applies `orchestration` after `batch` and
    `serving`;
  - the orchestration stack receives Glue job names and the projection Lambda
    ARN from Terraform outputs;
  - `batch_pipeline_schedule_enabled=false` is passed by default.
- Added static tests for orchestration structure, schedule defaults, DynamoDB
  lock behavior, outputs and workflow integration.
- Updated docs:
  - `cadrage.md`;
  - `docs/aws-service-iam-decisions.md`;
  - `infra/aws/README.md`;
  - `infra/aws/orchestration/README.md`.

No RDS/PostgreSQL AWS target, new historical datastore, direct Streamlit AWS
SDK access or broad data pipeline refactor was introduced.

## Validation Completed

Repository state and source control:

- `git status --short --untracked-files=all` was checked before changes.

Static/local validation:

- Host `python` failed because the WindowsApps Python launcher could not create
  the process. `py` was not installed. The repo Docker test path was used
  instead.
- First `powershell -ExecutionPolicy Bypass -File .\platform.ps1 test` failed
  on Docker access:
  `C:\Users\julie\.docker\config.json: Access is denied` and Docker pipe
  access denied.
- After approved Docker access,
  `powershell -ExecutionPolicy Bypass -File .\platform.ps1 test` passed:
  56 tests OK, 1 skipped because the local Spark classpath lacks the
  `spark-avro` package.
- `terraform fmt -check -recursive infra/aws` passed.
- Initial Terraform provider initialization for `infra/aws/orchestration`
  failed because sandboxed network access to `registry.terraform.io` was
  blocked.
- After approved provider-initialization network access,
  `terraform -chdir=infra/aws/orchestration init -backend=false -input=false`
  succeeded with `hashicorp/aws v5.100.0`.
- `terraform -chdir=infra/aws/core validate` passed.
- `terraform -chdir=infra/aws/batch validate` passed.
- `terraform -chdir=infra/aws/serving validate` passed.
- `terraform -chdir=infra/aws/orchestration validate` passed.
- `git diff --check` passed with LF/CRLF normalization warnings on Windows.

Runtime and deployment availability checks:

- No AWS runtime checks, Terraform apply, Step Functions execution,
  EventBridge schedule activation, Glue run or Lambda invocation were executed
  in this phase.

## Proof Obtained

- The repository now contains a Terraform-managed orchestration stack for the
  scheduled AWS batch chain after Raw.
- The state machine statically encodes the intended order:
  Bronze -> Silver -> Gold -> latest projection.
- The EventBridge Scheduler expression is `rate(1 minute)`, but the schedule
  is disabled by default.
- The state machine uses a DynamoDB conditional lock so a one-minute trigger
  can exit cleanly when a previous run still owns the lock.
- GitHub Actions deployment wiring now applies the orchestration stack after
  `batch` and `serving` and keeps the schedule disabled by default.
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
- `build/aws-runtime-evidence.json` from a real AWS runtime-validation run.
- EventBridge Scheduler actually triggering the Step Functions state machine.
- Step Functions executing Bronze, Silver, Gold and latest projection in AWS.
- The DynamoDB lock preventing overlapping real one-minute executions.
- Safe enabling of `batch_pipeline_schedule_enabled=true` in a bounded POC
  runtime window.

## Next Recommended Phase

Perform the one-time GitHub/AWS bootstrap described in `infra/aws/README.md`,
then run the GitHub Actions workflow through a push to `main` or
`workflow_dispatch` with the orchestration schedule still disabled.

If bootstrap is complete and the workflow succeeds, record the Terraform
outputs for `core`, `batch`, `serving` and `orchestration`, then run a
controlled AWS runtime-validation pass. Enable
`batch_pipeline_schedule_enabled=true` only in a bounded validation/demo window
after the first manual orchestration run proves Bronze -> Silver -> Gold ->
latest projection.

If the workflow or runtime validation fails, recommend one targeted remediation
phase named after the failing surface, for example OIDC trust, Terraform state,
ECR artifact publication, ECS/Kinesis, Glue Raw, Glue Bronze/Silver, Glue Gold,
Athena, Step Functions/Scheduler, DynamoDB projection or API Gateway/Cognito.

Ready-to-use next-agent prompt:

```text
Mission:
Run the deployed GitHub Actions path in a real AWS/GitHub environment after
completing the bootstrap in infra/aws/README.md, then validate the scheduled
batch orchestration in a controlled window.

Before doing anything, read AGENTS.md, cadrage.md, docs/phase-handoff.md,
infra/aws/README.md, infra/aws/orchestration/README.md and
.github/workflows/aws-deploy.yml. Confirm GitHub Environment dev has
AWS_ACCOUNT_ID, AWS_DEPLOY_ROLE_ARN, AWS_REGION, AWS_ARTIFACT_BUCKET,
TF_STATE_BUCKET, TF_STATE_REGION, VPC_ID, FARGATE_SUBNET_IDS,
STREAMLIT_CALLBACK_URLS, STREAMLIT_LOGOUT_URLS and API_CORS_ALLOWED_ORIGINS.
Confirm the AWS OIDC provider, deploy role trust, state bucket and S3 lockfile
permissions exist.

Run the workflow from GitHub, not with local long-lived AWS keys. Keep
batch_pipeline_schedule_enabled=false for the normal deployment. Capture exact
evidence from the GitHub run, Terraform outputs and build/aws-runtime-evidence.json.
For the orchestration proof, first start the Step Functions state machine in a
controlled manual run and verify Bronze -> Silver -> Gold -> latest projection.
Only then enable the one-minute schedule in a bounded POC window. Do not claim
AWS runtime proof if any bootstrap, permission or service check is missing.
```

## Suggested Commit Message

```text
feat: add scheduled AWS batch orchestration
```
