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
| Source | Binance Kline/Candlestick data | Fait on-prem, Prepare AWS producer, AWS lake ingestion a cadrer | Local producer and Kafka path exist; `apps/binance-producer/aws.py` prepares Kinesis publishing. Consuming Kinesis into AWS Raw/Bronze/Silver remains to cadrer. |
| Symbols | `BTCUSDC`, `ETHUSDC`, `SOLUSDC` | Fait on-prem, Prepare AWS | Existing producer/services and Terraform partition projection use these symbols. |
| Timeframes | `1s`, `1m`, `15m`, `1h` | Fait on-prem, Prepare AWS | Existing local config and Terraform projection expose these intervals. |
| Grain | one closed candle per `(symbol, interval, open_time)` | Fait on-prem | Silver rules and tests cover deduplication/closed-candle semantics. |
| Medallion layers | Raw, Bronze, Silver, Gold, Serving | Fait on-prem, Prepare AWS core/batch, AWS Raw/Bronze/Silver a cadrer | On-prem chain is proven; AWS producer and batch are prepared statically, but Kinesis -> S3 Raw/Bronze/Silver is still missing. |
| Daily volume reference | 263880 rows/day per main layer | Prepare | Captured as sizing context, not enforced by runtime tests yet. |
| Budget | 50 EUR maximum for controlled POC | Prepare, Budgets reporte | FinOps rules are documented; AWS Budgets must be cadre later before implementation. |
| Deployment | Terraform plus CI/CD | Prepare, CI/CD a developper | Terraform exists for batch and core producer resources; CI/CD still has to automate ECR image builds and versioned Glue artifacts. |

## Service decisions

| Need | Selected service | Repo status | Notes |
|---|---|---|---|
| Streaming ingestion | Kinesis Data Streams | Prepare | `infra/aws/core` declares the Kinesis stream and `apps/binance-producer/aws.py` publishes canonical JSON records with `symbol|interval` partition keys. AWS runtime proof is missing. |
| Long-running WebSocket producer | ECS Fargate, with EC2 as FinOps alternative | Prepare | `infra/aws/core` declares ECR, ECS/Fargate, IAM and logs for one configured producer service. EC2 remains only a documented FinOps alternative. |
| Batch ingestion | Lambda with EventBridge Scheduler | Reporte, a cadrer later | Periodic REST ingestion can be reconsidered later. The immediate missing ingestion scope is Kinesis -> S3 Raw/Bronze/Silver, not a separate Lambda batch path. |
| Batch processing | AWS Glue Spark batch | Prepare | `infra/aws/batch` creates a Glue Spark job for `jobs/gold-indicators/aws.py`; runtime AWS proof is missing. |
| Streaming processing | Glue Streaming ETL or justified alternative | A cadrer | Next phase must decide how Kinesis records become Raw, Bronze and Silver S3 datasets. Should run only in controlled demo windows if Glue Streaming is selected. |
| Storage | S3 with partitioned Parquet for Raw/Bronze/Silver/Gold | Prepare for Gold/batch, Raw/Bronze/Silver a cadrer | Terraform creates S3 lake paths and Glue tables for the current batch path; Raw/Bronze/Silver S3 ingestion from Kinesis is not designed or implemented yet. |
| Catalog | AWS Glue Data Catalog | Prepare | Terraform declares `silver`, `gold` and `trading_gold` databases/tables. |
| Analytics SQL | Athena on cataloged S3 tables | Prepare | Terraform declares an Athena workgroup/output location; query execution is not proven. |
| Low-latency latest metrics | DynamoDB | Reporte, a cadrer later | Latest metrics cache only, not historical source of truth. Cadrer after the producer/lake/Glue core path. |
| API backend | API Gateway plus Lambda | Reporte, a cadrer later | Exposure layer for dashboard/API use cases; not part of the next core AWS phase. |
| Dashboard | Streamlit Cloud or local for POC | Reporte, a cadrer later | Chosen for FinOps; prepare after API/latest-metrics boundaries are defined. |
| Observability | CloudWatch Logs, alarms, AWS Budgets | Prepare/Reporte | Glue and ECS producer log groups exist in Terraform; alarms and budgets require a later cadrage before implementation. |

Services explicitly rejected for this POC path: MSK, EMR, RDS, Redshift and
Lake Formation. RDS/PostgreSQL must not be introduced as an AWS target for this
project scope.

## IAM role decisions

| IAM role | Expected access | Repo status | Notes |
|---|---|---|---|
| `ecs-binance-producer-role` | Write Kinesis, write CloudWatch logs | Prepare | `infra/aws/core` declares a task role scoped to the configured Kinesis stream and an execution role scoped to ECR image pull plus producer logs. AWS runtime proof is missing. |
| `lambda-batch-ingestion-role` | Write S3 Raw/Bronze, write CloudWatch logs | Reporte, a cadrer later | Not the next phase. Reconsider only after the Kinesis -> S3 lake ingestion path is designed. |
| `glue-streaming-role` | Read Kinesis, read/write Raw/Bronze/Silver S3, Glue Catalog, logs | A cadrer | Next phase must define this role or an equivalent least-privilege role for the chosen Kinesis -> S3 processing pattern. |
| `glue-batch-role` | Read/write required S3 prefixes, Glue Catalog, logs | Prepare | Terraform creates `${project}-${env}-glue-batch-role` with prefix-scoped S3 access. |
| `lambda-api-role` | Read DynamoDB, limited Athena queries, logs | Reporte, a cadrer later | API target role; not part of the next core AWS phase. |
| `athena-query-role` | Read S3 Gold/trading_gold, Glue Catalog | A cadrer | Current Terraform creates an Athena workgroup, not a separate query role. |
| `monitoring-role` | Read metrics, logs and budgets | Reporte, a cadrer later | Monitoring and FinOps target role; cadrer after core AWS path. |

IAM rule to preserve: each component gets a dedicated least-privilege role.
Ingestion must not be able to modify Silver or Gold directly. Glue jobs should
be scoped to the input/output prefixes they consume and produce.

## Specification verification

| Specification | Status | Comment |
|---|---|---|
| Keep PostgreSQL on-prem only | Fait | Docs and tests keep RDS/PostgreSQL out of AWS scope. |
| AWS batch starts with S3/Glue/Athena | Prepare | Terraform stack exists and validates locally. |
| Cadrer producer/Kinesis/ECS/ECR and Glue packaging before implementation | Fait | The cadrage is documented in `docs/aws-core-portability-cadrage.md`; static implementation now exists for the producer core. |
| Cadrer Kinesis -> S3 Raw/Bronze/Silver before AWS runtime validation | A cadrer | This is the next phase. Do not jump to global AWS runtime validation before this lake ingestion path is framed and implemented. |
| Defer DynamoDB/API/Lambda/Streamlit/advanced monitoring until dedicated cadrage | Reporte | These services are target decisions, but they should not be implemented before the core producer/lake/Glue path is cadre. |
| Gold indicators stay in Gold | Fait | On-prem Gold and AWS entry point both use shared indicator logic. |
| Restitution tables are `trading_gold.*` on AWS | Prepare | Terraform declares Glue tables and the AWS job writes Parquet paths. |
| Partition analytical datasets by date, symbol and interval | Prepare | Glue table projection uses `event_date`, `symbol`, `interval` where applicable. |
| Use CloudWatch logs for Glue batch | Prepare | Log group and Glue continuous log arguments are declared. |
| Apply least privilege IAM | Prepare | Glue batch policy is scoped to batch S3 prefixes, Glue Catalog and logs. |
| Validate AWS runtime on S3/Glue/Athena | Reporte | Blocked until AWS credentials and target account access are available. |
| Configure AWS Budgets | Reporte, a cadrer later | Required for full FinOps target, not part of current batch stack or next core cadrage. |

## Next phase stance

The AWS core implementation is prepared statically: Kinesis producer entry
point, ECR/ECS/Fargate Terraform, producer IAM and versioned Glue artifact keys
exist in the repo. The next phase is not AWS runtime validation. The next phase
is the technical cadrage of the still-missing Kinesis -> S3 Raw/Bronze/Silver
lake ingestion path.

Runtime validation in AWS should happen only after the selected AWS path has
been framed and implemented: producer/Kinesis/ECS, Kinesis -> S3
Raw/Bronze/Silver, Glue Gold/trading_gold and any later API/dashboard/
observability surfaces explicitly included in scope.

Runtime proof remains separate: S3, Glue, Athena, DynamoDB, API Gateway/Lambda,
Kinesis, Glue Streaming, Streamlit and Budgets are not considered validated
until checked in a real AWS account.

## Runtime proof boundary

The on-premise Silver -> Gold -> Serving path is proven on YARN, HDFS/Hive,
PostgreSQL and Spark History. The AWS path is currently prepared and statically
validated only. Do not mark AWS runtime validation complete until:

- Terraform plan/apply succeeds in the target AWS account.
- The producer/ECS/Kinesis path is deployed and sends records.
- Kinesis -> S3 Raw/Bronze/Silver ingestion is implemented and checked.
- Silver Parquet input exists in S3.
- The Glue batch job runs successfully.
- Gold and `trading_gold` Parquet outputs are visible in S3.
- Glue Data Catalog tables are visible.
- At least one Athena query succeeds.
