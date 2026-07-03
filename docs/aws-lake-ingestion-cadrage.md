# AWS lake ingestion cadrage

## Objective

Frame the missing AWS lake ingestion path before implementation:

```text
Kinesis -> S3 Raw -> S3 Bronze -> S3 Silver
```

This phase is documentation only. It does not add Glue jobs, Terraform
resources, scripts, tests or AWS runtime validation.

Current repo state:

- `apps/binance-producer/aws.py` publishes canonical Avro binary records to
  Kinesis with partition key `symbol|interval`.
- `infra/aws/core` prepares Kinesis, ECR, ECS/Fargate, IAM and producer logs.
- `infra/aws/batch` prepares the S3 lake bucket, Glue Catalog, Athena and the
  Gold batch Glue job.
- `jobs/gold-indicators/aws.py` reads Silver Parquet from S3 and writes Gold
  plus `trading_gold.*` Parquet datasets.
- The missing part is the production of Raw, Bronze and Silver datasets on S3.

Out of scope for this phase and the next implementation phase:

- DynamoDB latest metrics;
- API Gateway/Lambda;
- Streamlit or dashboard work;
- advanced CloudWatch alarms;
- AWS Budgets;
- RDS or PostgreSQL on AWS;
- global AWS runtime validation.

## Execution choice

Decision updated after the Bronze streaming refactor: use a minimal Glue/Spark
lake path with Raw and Bronze streaming, while keeping Silver deterministic as
batch:

1. Glue Streaming ETL captures Kinesis records into Raw S3.
2. Glue Streaming ETL decodes Raw S3 into Bronze S3 and rejected S3.
3. Glue Spark batch rebuilds Silver from Bronze S3.
4. The existing `jobs/gold-indicators/aws.py` continues to read Silver S3.

This keeps Raw as the replayable audit boundary and moves the first technical
decode/reject step closer to ingestion. Silver remains batch because it applies
closed-candle quality filtering and deduplication by
`(symbol, interval, open_time)` with the latest `ingested_at`; doing that as
append-only streaming Parquet would add state and update complexity without a
demonstrated need.

The next implementation should therefore add AWS entry points in the existing
logical job folders:

```text
jobs/raw-consumer/aws.py
jobs/bronze-ingestion/aws.py
jobs/silver-transformation/aws.py
```

Do not create parallel top-level AWS job folders.

Decision update after implementation planning: AWS Kinesis now uses Avro binary
records based on `contracts/market-candle/v1.avsc`, not UTF-8 JSON. This keeps
the AWS and local paths aligned on the canonical Avro contract while avoiding a
producer rewrite to Java. Full AWS Glue Schema Registry integration remains a
later cadrage topic because the official Kinesis integrations are mostly
Java/Serde oriented and would change the implementation scope.

## Raw AWS

### Source

Raw AWS consumes the Kinesis stream created by `infra/aws/core`. The producer
already writes one canonical market candle per Kinesis record:

- record data: Avro binary matching `contracts/market-candle/v1.avsc`;
- partition key: `symbol|interval`;
- producer source: `apps/binance-producer/aws.py`.

The AWS Raw adapter must not assume Confluent Avro framing. Local Kafka records
keep the Confluent magic byte and schema-id header; AWS Kinesis records carry
the direct Avro binary payload for this phase.

### S3 format

Raw S3 should be Parquet, append-only, one row per Kinesis record.

Default prefix to add in Terraform/config:

```text
raw/binance/market_candles
```

Raw preserves the source envelope and technical metadata. Required columns:

| Column | Meaning |
|---|---|
| `source` | constant `kinesis` |
| `stream_name` | source Kinesis stream name |
| `partition_key` | Kinesis partition key |
| `sequence_number` | Kinesis sequence number |
| `approximate_arrival_timestamp` | Kinesis arrival timestamp when available |
| `value` | original Avro binary payload |
| `payload_size_bytes` | record size for audit |
| `symbol` | parsed from partition key, `_unknown` if missing |
| `interval` | parsed from partition key, `_unknown` if missing |
| `is_avro_decodable` | true when Spark can decode the Avro payload |
| `ingested_at` | Glue processing timestamp |
| `ingestion_date` | `to_date(ingested_at)` |
| `ingestion_hour` | `hour(ingested_at)` |

Raw must keep invalid payloads. It records Avro decode status but does not drop
records. Bronze is responsible for schema decoding and rejection output.

### Partitions

Use the same operational partitioning intent as on-prem Raw:

```text
symbol=<symbol>/interval=<interval>/ingestion_date=<yyyy-MM-dd>/ingestion_hour=<0-23>/
```

`symbol` and `interval` come from the Kinesis partition key, not from decoded
business payload fields. This preserves Raw as an envelope layer.

### Checkpoints and errors

The Glue Streaming checkpoint must be stored in S3, outside the data prefixes:

```text
checkpoints/raw/binance/market_candles
```

Processing errors should fail and retry through the Glue/Kinesis checkpoint
when they are infrastructure errors. Payload errors should not fail the stream:
they remain in Raw with `is_avro_decodable` and are routed by Bronze to the
rejected S3 area.

## Bronze AWS

### Input and output

Bronze AWS reads Raw S3 as a Glue Streaming file source and writes decoded
Bronze S3.

Default prefix to add:

```text
bronze/market_candles
```

Rejected records should be written to a separate Parquet prefix:

```text
rejected/bronze/market_candles
```

The implementation uses Glue Streaming with explicit checkpoints. Replay still
starts from Raw S3 by using a fresh or dedicated Bronze checkpoint.

### Decoding

Bronze decodes `value` as canonical Avro using the fields from
`contracts/market-candle/v1.avsc`.

Implementation rule:

- keep the Spark Avro decoding helper in `jobs/utils`;
- local Bronze strips the Confluent Avro header before decoding;
- AWS Bronze decodes the direct Avro binary payload from Kinesis Raw;
- add `event_date = to_date(open_time)`;
- add `year`, `month` and `day` if the on-prem Bronze path keeps them;
- keep envelope-specific logic in entry points or small adapters.

### Valid Bronze columns

Valid Bronze should contain the canonical candle fields plus Bronze partition
helpers:

```text
event_id
source
symbol
interval
open_time
close_time
open
high
low
close
volume
quote_asset_volume
number_of_trades
taker_buy_base_asset_volume
taker_buy_quote_asset_volume
is_closed
ingested_at
event_date
year
month
day
```

The raw Kinesis sequence and raw payload should stay in Raw and rejected
datasets. Do not carry them into Silver.

### Technical validation

Bronze applies first technical validity checks only:

- payload is valid Avro according to `contracts/market-candle/v1.avsc`;
- Avro fields match the canonical contract names;
- required identity and time fields are present and castable;
- `event_date` can be derived from `open_time`;
- payload `symbol` and `interval` are present;
- duplicate `event_id` records are reduced for a deterministic rebuild.

OHLCV business quality rules and closed-candle filtering remain Silver
responsibilities through `utils.quality.apply_silver_quality_rules`.

Rejected Bronze records should preserve:

- Raw envelope identifiers: stream, partition key, sequence number;
- original `value`;
- `is_avro_decodable`;
- `bronze_error_reason`;
- `ingested_at`, `ingestion_date`, `ingestion_hour`.

Do not write rejected records back to Kafka in AWS. Use S3 rejected prefixes
and CloudWatch logs.

### Shared logic boundary

Belongs in `jobs/utils`:

- canonical Avro decoder helpers;
- partition-key parsing if reused;
- Bronze valid/rejected transformation functions;
- deterministic event-id dedup rule.

Belongs in `jobs/bronze-ingestion/aws.py`:

- Glue arguments;
- S3 input/output paths;
- write modes;
- Spark session creation;
- rejected-output path wiring.

## Silver AWS

### Input and output

Silver AWS reads Bronze S3 and writes clean Silver Parquet to the prefix already
expected by `infra/aws/batch` and `jobs/gold-indicators/aws.py`:

```text
silver/market_candles
```

Partition layout must stay:

```text
event_date=<yyyy-MM-dd>/symbol=<symbol>/interval=<interval>/
```

### Transformation rule

Silver AWS must reuse the same business rules as on-prem:

- keep only closed candles;
- apply OHLCV quality rules from `jobs/utils/quality.py`;
- deduplicate by `(symbol, interval, open_time)`;
- keep the latest row by `ingested_at`, then deterministic tie-break by
  `event_id`;
- output exactly `utils.market_schema.SILVER_COLUMNS`;
- partition with `utils.market_schema.SILVER_PARTITIONS`.

The pure `build_silver` logic currently lives in
`jobs/silver-transformation/main.py`. The next implementation should move that
pure DataFrame transformation into `jobs/utils` and have both on-prem
`main.py` and AWS `aws.py` import it. IO stays in entry points.

### Compatibility with Gold AWS

`jobs/gold-indicators/aws.py` reads Silver with:

```text
GOLD_SOURCE_COLUMNS = symbol, interval, open_time, close_time,
open, high, low, close, volume
```

The Silver AWS output must therefore guarantee:

- these columns exist with Spark-compatible types;
- `open_time` and `close_time` are timestamps, not raw epoch integers;
- `event_date`, `symbol` and `interval` are available as partition columns;
- no technical indicators are computed in Silver.

Do not change `jobs/gold-indicators/aws.py` for this lake ingestion
implementation unless a test proves an incompatibility in the Silver contract.

## Terraform, IAM and CI/CD

### Terraform scope

Keep `infra/aws/core` responsible for producer, Kinesis, ECR, ECS/Fargate and
producer logs.

For the next implementation, prefer extending `infra/aws/batch` instead of
creating a second lake bucket or broad Terraform refactor. That stack already
owns the S3 lake bucket, Silver prefix, Glue Catalog and Gold batch job.

Resources to add or frame there:

- Raw and Bronze dataset prefixes as variables/locals;
- rejected Bronze prefix;
- Raw streaming checkpoint prefix;
- Glue scripts/artifacts for Raw, Bronze and Silver entry points;
- Glue Streaming job for Kinesis -> Raw;
- Glue Streaming job for Raw -> Bronze;
- Glue batch job for Bronze -> Silver;
- optional Glue Catalog tables for Raw and Bronze if they help inspection;
- CloudWatch log groups for lake ingestion jobs.

Do not add DynamoDB, Lambda, API Gateway, Streamlit, AWS Budgets, RDS or
PostgreSQL resources.

### IAM

Use dedicated least-privilege roles.

Raw streaming role:

- read only the configured Kinesis stream;
- write only Raw S3, raw checkpoint/temp prefixes and logs;
- read bucket location and list only required prefixes.

Lake transform role:

- read Raw S3 for Bronze;
- write Bronze S3 and Bronze rejected S3;
- read Bronze S3 for Silver;
- write Silver S3;
- access Glue Catalog only for the lake databases/tables it needs;
- write CloudWatch logs and Spark event/temp data.

Neither role should write Gold, `trading_gold`, DynamoDB, PostgreSQL or API
resources.

### CI/CD responsibility

Terraform creates durable resources and references artifact keys.

CI/CD should later:

- run unit/static tests;
- package `jobs/utils`;
- upload the Raw, Bronze and Silver AWS scripts;
- upload the contract file used by the Avro decoder at runtime;
- publish immutable artifact versions;
- pass the selected artifact version to Terraform.

The current local-dev Terraform upload pattern can remain for static
preparation, but the handoff must keep CI-produced immutable artifacts as the
target practice.

## Tests and validation expected in the next phase

Static/unit tests to add or update:

- producer Avro sample decodes into the canonical contract fields;
- invalid Avro goes to the Bronze rejected transformation;
- valid Bronze output contains the expected canonical columns and partitions;
- Silver AWS transformation matches `build_silver` rules and
  `SILVER_COLUMNS`;
- Silver output contains all `GOLD_SOURCE_COLUMNS`;
- Terraform scans still show no AWS PostgreSQL/RDS, DynamoDB, Lambda, API
  Gateway or Budgets resources;
- docs keep AWS runtime proof separate from static implementation.

Validation commands for implementation should stay static/local until an AWS
account is available:

```powershell
powershell -ExecutionPolicy Bypass -File .\platform.ps1 test
terraform fmt -check -recursive infra/aws
terraform -chdir=infra/aws/batch validate
terraform -chdir=infra/aws/core validate
rg -n "aws_db|aws_rds|postgres|postgresql" infra/aws -g "*.tf"
rg -n "aws_dynamodb|aws_lambda|aws_api_gateway|aws_apigateway|aws_budgets_budget" infra/aws -g "*.tf"
```

Do not run `terraform plan`, Glue jobs or AWS runtime checks unless credentials
and an explicit runtime-validation phase are available.

## Next implementation prompt

```text
Mission:
Implement the AWS lake ingestion path defined in
docs/aws-lake-ingestion-cadrage.md.

Before changes, read AGENTS.md, cadrage.md, docs/phase-handoff.md,
docs/phase-template.md, docs/aws-service-iam-decisions.md,
docs/aws-phase-prompts.md, docs/aws-core-portability-cadrage.md and
docs/aws-lake-ingestion-cadrage.md. Then inspect git status, rg results and the
actual Raw/Bronze/Silver/Gold/producers/Terraform files.

In scope:
- add AWS entry points in jobs/raw-consumer, jobs/bronze-ingestion and
  jobs/silver-transformation;
- move reusable Raw/Bronze/Silver transformations and schemas into jobs/utils
  where needed;
- keep IO, Glue arguments, S3 paths and checkpoints in entry points/adapters;
- extend infra/aws/batch for Raw/Bronze/Silver prefixes, Glue jobs, IAM, logs
  and artifact packaging;
- add focused unit/static tests for Avro decode, rejected payloads, Silver
  contract compatibility and forbidden AWS services;
- update docs/phase-handoff.md with exact validation results and missing proof.

Out of scope:
- AWS runtime validation;
- terraform plan/apply unless explicitly authorized in a later runtime phase;
- DynamoDB latest metrics;
- API Gateway/Lambda;
- Streamlit/dashboard;
- advanced CloudWatch alarms;
- AWS Budgets;
- RDS/PostgreSQL AWS.
```

## Proof boundary

This cadrage decides the implementation shape only. It does not prove:

- Kinesis records are received in AWS;
- Glue Streaming reads Kinesis;
- Raw/Bronze/Silver S3 datasets exist;
- Silver S3 is readable by the Gold Glue job;
- Glue Catalog/Athena expose the new lake layers;
- any AWS runtime path is operational.
