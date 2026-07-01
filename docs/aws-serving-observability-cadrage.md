# AWS serving, API and observability cadrage

## Objective

Frame the later AWS restitution, API, Streamlit and observability scope before
implementation. This phase is documentation only. It does not add Terraform
resources, Lambda code, DynamoDB tables, Streamlit code, CI/CD or AWS runtime
validation.

Current prepared AWS data path:

```text
Kinesis -> S3 Raw -> S3 Bronze -> S3 Silver
-> Glue Spark Gold -> trading_gold S3 -> Glue Data Catalog -> Athena
```

The historical analytical source of truth remains S3, Glue Data Catalog and
Athena. PostgreSQL remains an on-premise Serving target only.

## Current repo state

- `jobs/gold-indicators/aws.py` reads Silver Parquet from S3, computes Gold
  indicators, then materializes the same restitution tables as on-premise
  Serving under `trading_gold.*`.
- `jobs/serving-datamart/sql/market_indicators_latest.sql` produces one latest
  row per `(symbol, interval)`.
- `infra/aws/batch` declares Glue Catalog tables for:
  - `trading_gold.market_indicators`;
  - `trading_gold.market_indicators_latest`;
  - `trading_gold.market_multitimeframe_signals`;
  - `trading_gold.market_daily_summary`.
- `infra/aws/core` and `infra/aws/batch` already create CloudWatch log groups
  for the producer and Glue jobs.
- No Terraform resource currently exists for DynamoDB, Lambda, API Gateway,
  Cognito, Streamlit, AWS Budgets, RDS or PostgreSQL.

## DynamoDB latest metrics

Decision: DynamoDB is a low-latency latest-metrics cache only. It is not the
historical analytical source of truth and does not replace Athena.

Source:

- preferred source: `trading_gold.market_indicators_latest`;
- acceptable implementation source: the same latest restitution DataFrame
  produced after Gold, before or after writing the S3 dataset;
- forbidden source: Raw, Bronze, Silver, direct Binance/Kinesis records or API
  Lambda recomputation.

Table shape to implement later:

| Item | Decision |
|---|---|
| Table role | Latest metrics cache/projection |
| Partition key | `symbol` |
| Sort key | `interval` |
| Stored data | `open_time`, `close_time`, OHLCV, EMA/MACD/RSI/Bollinger, `event_date`, `updated_at` |
| Optional TTL | `expires_at_epoch`, POC default 7 days |
| Freshness check | API checks `updated_at`; TTL is cleanup, not correctness |

The writer must be a dedicated projection step after Gold/restitution. It can be
implemented later as a small Glue/Python/Lambda projection, but it must not be
the API Lambda. It must overwrite/upsert only latest items keyed by
`(symbol, interval)` and must not store historical candles.

## API Gateway and Lambda

Decision: API Gateway plus Lambda is the public data exposure layer. It reads
prepared datasets and caches; it does not compute indicators or mutate the lake.

Candidate endpoints:

| Endpoint | Source | Notes |
|---|---|---|
| `GET /health` | none | Returns service/config health only, no sensitive data |
| `GET /metrics/latest?symbol=&interval=` | DynamoDB | Fast latest metrics path |
| `GET /metrics/history?symbol=&interval=&from=&to=&limit=&next_token=` | Athena | Reads `trading_gold.market_indicators` |
| `GET /signals?symbol=&from=&to=&limit=&next_token=` | Athena | Reads `trading_gold.market_multitimeframe_signals` |
| `GET /daily-summary?symbol=&from=&to=&limit=&next_token=` | Athena | Reads `trading_gold.market_daily_summary` |

Response and error rules:

- JSON responses use ISO timestamps and numeric values as numbers.
- List endpoints return `items` and optional `next_token`.
- `limit` must be bounded, with a small POC default and a documented maximum.
- Use `400` for invalid query parameters, `401` for missing/invalid auth,
  `403` for forbidden access, `404` for a missing latest metric, `429` for
  throttling and `5xx` for service failures.
- Lambda must not expose raw Athena SQL input from users.

Lambda must not:

- calculate EMA, MACD, RSI or Bollinger;
- write Raw, Bronze, Silver, Gold or `trading_gold` S3 datasets;
- write the DynamoDB latest projection except in a separate projection Lambda;
- connect to PostgreSQL or introduce RDS;
- hold long-running Spark or Glue responsibilities.

Minimal IAM for the API Lambda:

- read only the selected DynamoDB latest table;
- start and read Athena queries in the selected workgroup;
- read required Glue Catalog metadata and Athena result objects;
- write only its own CloudWatch logs;
- no S3 write access to lake datasets.

## Cognito authentication

Decision: use Amazon Cognito for the AWS user boundary. Cognito protects both
the dashboard user flow and API Gateway.

Default auth shape:

- Cognito User Pool for POC users.
- Cognito Hosted UI with Authorization Code plus PKCE.
- App client for the Streamlit frontend.
- API Gateway JWT authorizer validates Cognito tokens.
- Simple groups: `viewer` and `admin`.

For the first implementation, `viewer` can read all API endpoints. `admin` is
reserved for later operational functions; no admin mutation endpoint is needed
in v1.

Do not put AWS IAM access keys in Streamlit Cloud. Streamlit should hold only
frontend/API configuration and Cognito public client settings. Data access goes
through API Gateway with the Cognito bearer token.

## Streamlit dashboard

Decision: Streamlit Cloud is the default POC target because it is the simplest
and cheapest consultation surface. It is not a source of truth.

Default flow:

```text
User -> Streamlit Cloud -> Cognito Hosted UI -> API Gateway/Lambda
-> DynamoDB latest or Athena -> JSON response
```

Streamlit rules:

- call API Gateway only;
- do not access DynamoDB, Athena, S3 or Glue directly;
- do not store AWS IAM keys;
- keep API URL, Cognito domain/client id and redirect URLs in Streamlit
  secrets/config;
- display latest metrics, historical indicators, multitimeframe signals and
  daily summaries from API responses;
- local development may use fixtures or a local API URL, clearly marked as not
  AWS runtime proof.

Alternative if AWS-hosted UI is required:

- ECS/Fargate behind an HTTPS ALB with Cognito authentication at the ALB or app
  layer;
- use this only if Streamlit Cloud is rejected by deployment constraints.

EC2 is not the v1 target. It remains a manual fallback only if a later decision
accepts instance maintenance for the demo.

## Observability and FinOps

Existing prepared observability:

- ECS producer CloudWatch log group in `infra/aws/core`;
- Glue job CloudWatch log group in `infra/aws/batch`;
- Glue metrics and Spark UI flags are prepared in Glue job arguments.

Alarms to implement later:

| Service | Minimal signals |
|---|---|
| Kinesis | write throttles, iterator age, incoming records/bytes |
| ECS producer | task stopped, service desired vs running count, log errors |
| Glue | job failures, runtime duration, retry/failure count |
| Lambda API | errors, throttles, duration, concurrent executions |
| API Gateway | 4xx, 5xx, latency, request count |
| DynamoDB | throttled reads/writes, consumed capacity, system errors |
| Athena | failed queries and scanned bytes trend |

FinOps rules:

- configure AWS Budgets for the 50 EUR controlled POC target;
- add warning thresholds such as 50%, 80% and 100%;
- keep CloudWatch log retention short for POC, aligned with current 14-day
  defaults unless a report need says otherwise;
- lifecycle Athena query results and temporary artifacts;
- keep historical Gold and `trading_gold` datasets by default, and make any
  destructive cleanup explicit and environment-scoped;
- prefer small provisioned/on-demand settings that match demo volume, then
  revisit with real CloudWatch metrics.

## Terraform, IAM and CI/CD framing

Terraform should later create durable resources:

- DynamoDB latest table and TTL setting;
- API Gateway HTTP API or REST API;
- Lambda functions, log groups and permissions;
- Cognito User Pool, Hosted UI domain, app client, groups and API authorizer;
- CloudWatch alarms, SNS notification topic if retained, and AWS Budgets;
- optional ECS/Fargate/ALB resources only if Streamlit Cloud is not retained.

CI/CD should later:

- package Lambda code;
- publish immutable artifacts;
- deploy Streamlit app configuration separately from AWS Terraform;
- run unit/static tests and Terraform validation before deployment;
- keep secrets outside the repository.

Expected secrets/config:

- Cognito domain, user pool id and app client id;
- API Gateway base URL;
- Athena workgroup/result location for Lambda;
- DynamoDB table name;
- no committed passwords, tokens or AWS access keys.

## Tests and validation expected in implementation

Static/local tests:

- DynamoDB projection maps `trading_gold.market_indicators_latest` rows to
  latest cache items with key `(symbol, interval)`.
- API parameter validation rejects missing/invalid symbols, intervals, dates
  and excessive limits.
- API responses keep stable JSON shapes for latest, history, signals and daily
  summary.
- Lambda handlers do not import Spark and do not contain indicator formulas.
- Terraform scans prove no RDS/PostgreSQL AWS resources are introduced.
- Streamlit code, if added, calls only API Gateway and does not import AWS SDKs
  for direct DynamoDB/Athena/S3 access.

Runtime proof, only in a later AWS validation phase:

- Cognito login succeeds through the selected redirect URI.
- API Gateway rejects unauthenticated requests and accepts valid Cognito JWTs.
- Latest endpoint reads a real DynamoDB item.
- History/signals/daily endpoints return Athena-backed data.
- Streamlit Cloud can authenticate and display API-backed data.
- CloudWatch alarms and AWS Budget are visible and configured.

Do not run `terraform plan`, `terraform apply`, AWS CLI checks or Streamlit
deployment during this cadrage phase.

## Next implementation prompt

```text
Mission:
Implement the AWS serving, API, Cognito, Streamlit Cloud and observability scope
defined in docs/aws-serving-observability-cadrage.md.

Before changes, read AGENTS.md, cadrage.md, docs/phase-handoff.md,
docs/phase-template.md, docs/aws-service-iam-decisions.md,
docs/aws-phase-prompts.md, docs/aws-core-portability-cadrage.md,
docs/aws-lake-ingestion-cadrage.md and
docs/aws-serving-observability-cadrage.md. Then inspect git status, rg results,
the existing trading_gold tables, Terraform stacks and tests.

In scope:
- DynamoDB latest metrics projection from trading_gold.market_indicators_latest;
- API Gateway/Lambda read API for latest, history, signals and daily summary;
- Cognito User Pool, Hosted UI, app client, groups and API JWT authorizer;
- Streamlit Cloud wiring through API Gateway only;
- CloudWatch alarms and AWS Budgets for the controlled POC;
- least-privilege IAM and static/local tests;
- documentation and phase handoff updates.

Out of scope:
- AWS runtime validation;
- terraform plan/apply unless explicitly authorized in a later runtime phase;
- direct Streamlit access to DynamoDB, Athena, S3 or Glue;
- RDS/PostgreSQL AWS;
- replacing S3/Glue/Athena as the historical analytical source.
```

## Proof boundary

This cadrage decides the implementation shape only. It does not prove:

- any DynamoDB table exists;
- API Gateway, Lambda or Cognito are deployed;
- Streamlit Cloud is configured;
- alarms or budgets exist;
- any AWS runtime path is operational.
