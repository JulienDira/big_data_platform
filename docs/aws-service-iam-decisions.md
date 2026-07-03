# AWS service and IAM decisions

This document is the repo-readable synthesis of `Cahier des charges.docx`.
The `.docx` remains the raw business document. This Markdown file records the
project decisions in a format that agents and reviewers can inspect quickly.

## Current status

Status values:

- `Fait`: implemented and locally or runtime validated in the repo.
- `Prepare`: code or Terraform exists, but runtime proof is still missing.
- `A cadrer`: target decision exists, but packaging, IAM, deployment or
  runtime responsibilities must be specified before implementation.
- `A developper`: cadrage is done or explicitly accepted, but implementation is
  not in the repo yet.
- `Reporte`: target decision exists, but it is intentionally left for a later
  phase.
- `Non conforme`: visible repo state conflicts with the cahier des charges.

| Area | Cahier des charges decision | Repo status | Evidence |
|---|---|---|---|
| Source | Binance Kline/Candlestick data | Fait on-prem, Prepare AWS producer/lake ingestion | Local producer and Kafka path exist; `apps/binance-producer/aws.py` prepares Kinesis publishing with Avro binary payloads, and AWS lake jobs now prepare Kinesis -> S3 Raw/Bronze/Silver. AWS runtime proof is missing. |
| Symbols | `BTCUSDC`, `ETHUSDC`, `SOLUSDC` | Fait on-prem, Prepare AWS | Existing producer/services and Terraform partition projection use these symbols. |
| Timeframes | `1s`, `1m`, `15m`, `1h` | Fait on-prem, Prepare AWS | Existing local config and Terraform projection expose these intervals. |
| Grain | one closed candle per `(symbol, interval, open_time)` | Fait on-prem | Silver rules and tests cover deduplication/closed-candle semantics. |
| Medallion layers | Raw, Bronze, Silver, Gold, Serving | Fait on-prem, Prepare AWS core/lake/batch | On-prem chain is proven; AWS producer, Kinesis -> S3 Raw/Bronze/Silver and Gold batch paths are prepared statically. AWS runtime proof is missing. |
| Daily volume reference | 263880 rows/day per main layer | Prepare | Captured as sizing context, not enforced by runtime tests yet. |
| Budget | 50 EUR maximum for controlled POC | Prepare | `infra/aws/serving` declares an AWS Budget with 50%, 80% and 100% notification thresholds when an alert email is provided. AWS runtime proof is missing. |
| Deployment | Terraform plus CI/CD | Prepare, CI/CD/runtime validation implemente statiquement | Terraform exists for core, batch, serving and orchestration resources; `.github/workflows/aws-deploy.yml` uses job-scoped GitHub Actions OIDC, immutable ECR/S3 artifacts, Lambda Zip/S3 packaging, S3 backend lockfiles and a controlled runtime-validation job. GitHub/AWS execution proof is still missing. |

## Service decisions

| Need | Selected service | Repo status | Notes |
|---|---|---|---|
| Streaming ingestion | Kinesis Data Streams | Prepare | `infra/aws/core` declares the Kinesis stream and `apps/binance-producer/aws.py` publishes canonical Avro binary records with `symbol|interval` partition keys. AWS runtime proof is missing. |
| Schema governance | Canonical Avro contract, Glue Schema Registry later if needed | Prepare, registry reporte | `contracts/market-candle/v1.avsc` remains the canonical contract. Full Glue Schema Registry integration is intentionally deferred because it changes the producer/runtime scope. |
| Long-running WebSocket producer | ECS Fargate, with EC2 as FinOps alternative | Prepare | `infra/aws/core` declares ECR, ECS/Fargate, IAM and logs for one configured producer service. EC2 remains only a documented FinOps alternative. |
| Batch ingestion | Lambda with EventBridge Scheduler | Reporte, a cadrer later | Periodic REST ingestion can be reconsidered later. The immediate missing ingestion scope is Kinesis -> S3 Raw/Bronze/Silver, not a separate Lambda batch path. |
| Batch processing | AWS Glue Spark batch | Prepare | `infra/aws/batch` creates a Glue Spark job for `jobs/gold-indicators/aws.py`; runtime AWS proof is missing. |
| Batch orchestration | EventBridge Scheduler plus Step Functions | Prepare | `infra/aws/orchestration` prepares a disabled-by-default `rate(1 minute)` schedule, a Step Functions chain Bronze -> Silver -> Gold -> latest projection and a DynamoDB conditional lock. AWS runtime proof is missing. |
| Streaming processing | Glue Streaming ETL for Raw capture, Glue Spark batch for Bronze/Silver | Prepare | `infra/aws/batch` declares Glue jobs for Avro Kinesis -> Raw S3, Raw -> Bronze and Bronze -> Silver. AWS Glue execution is not proven. |
| Storage | S3 with partitioned Parquet for Raw/Bronze/Silver/Gold | Prepare | Terraform creates S3 lake paths for Raw, Bronze, rejected, Silver, Gold and `trading_gold`. S3 runtime writes are not proven. |
| Catalog | AWS Glue Data Catalog | Prepare | Terraform declares Raw, Bronze, Silver, Gold and `trading_gold` databases/tables. |
| Analytics SQL | Athena on cataloged S3 tables | Prepare | Terraform declares an Athena workgroup/output location; query execution is not proven. |
| Low-latency latest metrics | DynamoDB | Prepare | `infra/aws/serving` declares the latest metrics table keyed by `symbol` and `interval`; `apps/aws-serving-api/projection_handler.py` projects from `trading_gold.market_indicators_latest`. AWS runtime proof is missing. |
| API backend | API Gateway plus Lambda | Prepare | `infra/aws/serving` declares a read-only HTTP API and Lambda for latest metrics, history, signals and daily summary. Lambda code does not compute indicators or write lake datasets. AWS runtime proof is missing. |
| Dashboard | Streamlit Cloud by default, ECS/Fargate alternative if AWS-hosted UI is required | Prepare | `apps/streamlit-dashboard` is wired for Cognito Hosted UI and API Gateway only. No Streamlit Cloud deployment has been performed. |
| Authentication | Amazon Cognito | Prepare | `infra/aws/serving` declares User Pool, Hosted UI domain, public Streamlit app client, `viewer` / `admin` groups and API Gateway JWT authorizer. AWS runtime proof is missing. |
| Observability | CloudWatch Logs, alarms, AWS Budgets | Prepare | `infra/aws/serving` declares Lambda/API log groups, minimal CloudWatch alarms, optional SNS alerts, Glue failure event rule and AWS Budget. AWS runtime proof is missing. |

Services explicitly rejected for this POC path: MSK, EMR, RDS, Redshift and
Lake Formation. RDS/PostgreSQL must not be introduced as an AWS target for this
project scope.

## IAM role decisions

| IAM role | Expected access | Repo status | Notes |
|---|---|---|---|
| `ecs-binance-producer-role` | Write Kinesis, write CloudWatch logs | Prepare | `infra/aws/core` declares a task role scoped to the configured Kinesis stream and an execution role scoped to ECR image pull plus producer logs. AWS runtime proof is missing. |
| `lambda-batch-ingestion-role` | Write S3 Raw/Bronze, write CloudWatch logs | Reporte, a cadrer later | Not the next phase. Reconsider only after the Kinesis -> S3 lake ingestion path is designed. |
| `glue-raw-streaming-role` | Read Kinesis, write Raw S3, write Raw checkpoint/temp prefixes and logs | Prepare | Terraform declares the dedicated Raw streaming role and policy. AWS role execution is not proven. |
| `glue-lake-transform-role` | Read Raw/Bronze S3, write Bronze/Silver/rejected S3, Glue Catalog and logs | Prepare | Terraform declares the dedicated Bronze/Silver transform role and policy. It must not write Gold, `trading_gold`, DynamoDB, API resources or PostgreSQL. |
| `glue-batch-role` | Read/write required S3 prefixes, Glue Catalog, logs | Prepare | Terraform creates `${project}-${env}-glue-batch-role` with prefix-scoped S3 access. |
| `batch-pipeline-sfn-role` | Start/read Glue batch jobs, invoke latest projection Lambda, manage the DynamoDB orchestration lock, write Step Functions logs | Prepare | `infra/aws/orchestration` declares the Step Functions execution role. Runtime execution is not proven. |
| `batch-pipeline-scheduler-role` | Start the batch pipeline Step Functions state machine | Prepare | `infra/aws/orchestration` declares the EventBridge Scheduler target role. The schedule is disabled by default. |
| `lambda-api-role` | Read DynamoDB latest table, start/read bounded Athena queries, read required Glue/S3 Athena result metadata, write logs | Prepare | `infra/aws/serving` scopes the API Lambda role to DynamoDB reads, selected Athena workgroup, `trading_gold` Glue metadata, Athena result prefix and logs. It does not write lake datasets or connect to PostgreSQL. |
| `dynamodb-latest-projection-role` | Read `trading_gold.market_indicators_latest`, write latest cache items, write logs | Prepare | `infra/aws/serving` declares a dedicated projection Lambda role. The API Lambda does not own projection writes. |
| `cognito-auth-surface` | User Pool, Hosted UI, app client, groups and API Gateway JWT authorizer | Prepare | `infra/aws/serving` declares the Cognito User Pool, Hosted UI domain, public app client, `viewer` / `admin` groups and API JWT authorizer. |
| `athena-query-role` | Read S3 Gold/trading_gold, Glue Catalog, Athena result location | Prepare | Athena access is scoped inside the API and projection Lambda roles rather than a standalone role; both use the selected workgroup and Athena result prefix only. |
| `monitoring-role` | Read metrics, logs and budgets; publish notifications if SNS is retained | Prepare | `infra/aws/serving` declares alarms, optional SNS topic/subscription and AWS Budget. Runtime proof is missing. |

IAM rule to preserve: each component gets a dedicated least-privilege role.
The Raw streaming role must not modify Bronze, Silver or Gold directly. The
lake transform role may write Bronze and Silver, but must not write Gold,
`trading_gold`, DynamoDB, API resources or PostgreSQL. Glue jobs should be
scoped to the input/output prefixes they consume and produce.

## Specification verification

| Specification | Status | Comment |
|---|---|---|
| Keep PostgreSQL on-prem only | Fait | Docs and tests keep RDS/PostgreSQL out of AWS scope. |
| AWS batch starts with S3/Glue/Athena | Prepare | Terraform stack exists and validates locally. |
| Cadrer producer/Kinesis/ECS/ECR and Glue packaging before implementation | Fait | The cadrage is documented in `docs/aws-core-portability-cadrage.md`; static implementation now exists for the producer core. |
| Cadrer and implement Kinesis -> S3 Raw/Bronze/Silver before AWS runtime validation | Prepare | Cadrage, jobs and Terraform exist in the repo. AWS runtime proof is still missing. |
| Cadrer DynamoDB/API/Lambda/Streamlit/Cognito/advanced monitoring before implementation | Prepare | Dedicated cadrage lives in `docs/aws-serving-observability-cadrage.md`; static implementation now exists under `apps/aws-serving-api`, `apps/streamlit-dashboard` and `infra/aws/serving`. AWS runtime proof is missing. |
| Gold indicators stay in Gold | Fait | On-prem Gold and AWS entry point both use shared indicator logic. |
| Restitution tables are `trading_gold.*` on AWS | Prepare | Terraform declares Glue tables and the AWS job writes Parquet paths. |
| Partition analytical datasets by date, symbol and interval | Prepare | Glue table projection uses `event_date`, `symbol`, `interval` where applicable. |
| Use CloudWatch logs for Glue batch | Prepare | Log group and Glue continuous log arguments are declared. |
| Schedule the AWS batch chain after Raw | Prepare | EventBridge Scheduler and Step Functions are declared statically with a disabled default schedule and a DynamoDB single-flight lock. AWS runtime proof is missing. |
| Apply least privilege IAM | Prepare | Glue batch policy is scoped to batch S3 prefixes, Glue Catalog and logs. |
| Cadrer and implement CI/CD before AWS runtime validation | Prepare | `docs/aws-cicd-deployment-cadrage.md` defines the path and `.github/workflows/aws-deploy.yml` implements GitHub Actions OIDC, immutable artifact publication, Terraform/CI separation, Zip/S3 Lambda packaging, S3 lockfile backend config and controlled runtime validation. GitHub/AWS execution proof is still missing. |
| Verify AWS implementation step by step before deployment/runtime validation | Fait statiquement | `docs/aws-implementation-step-audit.md` verifies producer/core, Raw, Bronze/Silver, Gold/restitution, Serving/API/dashboard/observability and CI/CD in order. One Kinesis `PutRecords` partial-failure handling issue was corrected with tests. No AWS runtime or `terraform apply` was run. |
| Validate AWS runtime on S3/Glue/Athena | Reporte | Blocked until AWS credentials and target account access are available. |
| Configure AWS Budgets | Prepare | `infra/aws/serving` declares a 50 EUR monthly POC Budget with optional email notifications at 50%, 80% and 100%. AWS runtime proof is missing. |

## Next phase stance

The AWS core and lake ingestion implementation are prepared statically:
Kinesis producer entry point, ECR/ECS/Fargate Terraform, producer IAM,
versioned Glue artifact keys and Kinesis -> S3 Raw/Bronze/Silver jobs exist in
the repo.

The later restitution/API/observability scope is now statically implemented in
`apps/aws-serving-api`, `apps/streamlit-dashboard` and `infra/aws/serving`.
The static quality, standards and conformance audit is complete. The CI/CD and
artifact publication path is implemented statically. The step-by-step static
implementation verification is complete in
`docs/aws-implementation-step-audit.md` and leaves no blocking static issue.

The user-requested AWS automated deployment and runtime validation phase is now
implemented statically in the repo: the workflow is hardened for job-scoped
OIDC, action SHA pinning, S3 backend lockfiles, immutable artifacts and a
post-apply runtime-validation script. Runtime validation still depends on real
AWS/GitHub bootstrap and credentials.

The scheduled batch orchestration phase is also implemented statically:
`infra/aws/orchestration` declares EventBridge Scheduler, Step Functions, a
DynamoDB conditional lock and the Step Functions/Scheduler IAM roles. The
schedule remains disabled by default until a controlled AWS runtime window.

The normal deployment credential path must be GitHub Actions OIDC with a scoped
AWS role, not long-lived AWS access keys or an administrator IAM user. If a
temporary admin action is required for bootstrap, it must be documented as
manual bootstrap only.

AWS runtime validation should happen only after CI/CD publishes immutable
producer, Glue and Lambda artifacts, Terraform consumes those versions, the
dev/POC deployment path is reproducible, and a real AWS account, credentials,
callback URLs, alert email and deployment permissions are available.

Runtime validation in AWS should happen only after the selected AWS path has
been framed and implemented: producer/Kinesis/ECS, Kinesis -> S3
Raw/Bronze/Silver, Glue Gold/trading_gold and any later API/dashboard/
observability surfaces explicitly included in scope.

Runtime proof remains separate: S3, Glue, Athena, DynamoDB, API Gateway/Lambda,
Cognito, Kinesis, Glue Streaming, Step Functions, EventBridge Scheduler,
Streamlit and Budgets are not considered validated until checked in a real AWS
account.

## Runtime proof boundary

The on-premise Silver -> Gold -> Serving path is proven on YARN, HDFS/Hive,
PostgreSQL and Spark History. The AWS path is currently prepared and statically
validated only. Before marking AWS runtime validation complete, CI/CD artifact
publication, step-by-step static implementation verification and the automated
deployment path must be completed and checked in a real AWS account. Do not
mark AWS runtime validation complete until:

- CI/CD publishes the producer image, Glue artifacts and Lambda package with an
  immutable version.
- Terraform consumes those immutable versions through explicit inputs.
- Terraform plan/apply succeeds in the target AWS account.
- The producer/ECS/Kinesis path is deployed and sends records.
- Kinesis -> S3 Raw/Bronze/Silver ingestion is deployed and checked in AWS.
- Silver Parquet input exists in S3.
- The Glue batch job runs successfully.
- Gold and `trading_gold` Parquet outputs are visible in S3.
- Step Functions runs Bronze, Silver, Gold and latest projection in order.
- EventBridge Scheduler triggers the state machine only in a controlled window.
- Glue Data Catalog tables are visible.
- At least one Athena query succeeds.
