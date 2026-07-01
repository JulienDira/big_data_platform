# AWS core portability cadrage

## Objective

Define how the existing on-premise code should be reused on the AWS core path
before implementation. This phase does not add AWS runtime resources or code.

Current proven path:

```text
Binance REST -> Kafka/Schema Registry -> Raw HDFS -> Bronze HDFS
-> Silver Hive -> Gold Hive -> Serving PostgreSQL
```

Current prepared AWS batch path:

```text
Silver S3 -> Glue Spark -> Gold S3 -> trading_gold S3
-> Glue Data Catalog -> Athena
```

AWS runtime proof is still missing because no AWS credentials/account are
available in this environment.

## Repo audit summary

### Producer

Relevant files:

- `apps/binance-producer/main.py`
- `apps/binance-producer/model.py`
- `apps/binance-producer/Dockerfile`
- `apps/binance-producer/requirements.txt`
- `contracts/market-candle/v1.avsc`
- `tests/test_producer_model.py`

Current state:

- `model.py` contains the reusable normalization rule through
  `normalize_kline`.
- `main.py` fetches Binance REST klines, keeps an in-memory duplicate guard,
  serializes with Confluent Avro and publishes to Kafka.
- The Dockerfile already packages the producer app and `contracts/`.
- The current Python dependencies are Kafka-oriented:
  `confluent-kafka[avro]` and `requests`.
- The Avro file is the canonical event contract.

Decision:

- Keep `apps/binance-producer/main.py` as the on-premise Kafka entry point.
- Keep `apps/binance-producer/model.py` as the shared normalization layer.
- Add an AWS entry point in the same app folder, preferably
  `apps/binance-producer/aws.py`, instead of creating a parallel top-level AWS
  producer tree.
- The AWS entry point should reuse the same Binance fetch/normalization
  behavior and replace only the output adapter: Kafka producer out,
  Kinesis publisher in.
- For the first implementation, publish one canonical candle record per
  Kinesis record as UTF-8 JSON matching `contracts/market-candle/v1.avsc`.
  Do not introduce AWS Glue Schema Registry or another schema service unless a
  later cadrage explicitly chooses it.
- Use Kinesis partition keys in the same domain shape as Kafka keys:
  `symbol|interval`.
- Keep the first ECS deployment to one service/task handling configured CSV
  `MARKET_SYMBOLS` and `MARKET_INTERVALS`. Do not create twelve Fargate
  services by default; split by flow only if runtime proof shows a real need.

Producer environment variables for AWS:

- existing reusable values:
  - `BINANCE_BASE_URL`
  - `MARKET_SYMBOLS`
  - `MARKET_INTERVALS`
  - `PRODUCER_POLL_SECONDS`
  - `LOG_LEVEL`
- AWS-specific values:
  - `AWS_REGION`
  - `KINESIS_STREAM_NAME`
  - optional `KINESIS_PUBLISH_BATCH_SIZE`

IAM boundary:

- ECS task role may write records only to the configured Kinesis stream and
  write logs to its CloudWatch log group.
- ECS task execution role may pull the producer image from ECR and write ECS
  task logs.
- The producer must not read or write S3 Silver, Gold or `trading_gold`
  datasets directly.

## ECS, ECR and Kinesis Terraform strategy

Decision:

- Add a narrowly scoped Terraform module or stack under `infra/aws/core` for
  producer runtime resources:
  - Kinesis Data Stream;
  - ECR repository for the producer image;
  - ECS cluster, task definition and service;
  - ECS task role and task execution role;
  - CloudWatch log group for producer logs;
  - security group and subnet wiring for Fargate.
- Keep `infra/aws/batch` focused on S3, Glue, Glue Catalog and Athena.
- Do not add RDS/PostgreSQL, DynamoDB, API Gateway, Lambda, Streamlit,
  CloudWatch alarms or AWS Budgets in this core implementation phase.

Network stance:

- Fargate is the default runtime.
- For a controlled POC, allow public-subnet Fargate with `assign_public_ip`
  when no low-cost private egress path is available.
- Private subnets with NAT can be supported through variables later, but should
  be justified because NAT can dominate POC cost.
- EC2 remains an alternative only if a written FinOps tradeoff shows it is
  simpler or cheaper for the demo constraints.

Kinesis stream stance:

- Use one stream for market candles in the first implementation.
- Make shard mode/capacity configurable in Terraform.
- Start with the smallest controlled capacity that supports the current
  symbols and intervals. Confirm regional AWS pricing before applying.

## Glue and Spark batch strategy

Relevant files:

- `jobs/gold-indicators/aws.py`
- `jobs/gold-indicators/main.py`
- `jobs/utils/`
- `jobs/serving-datamart/registry.py`
- `jobs/serving-datamart/sql/`
- `infra/aws/batch`
- `infra/scripts/package-job-utils.py`
- `tests/test_gold_restitution_golden.py`
- `tests/test_serving_registry.py`
- `tests/test_serving_transformations.py`

Current state:

- On-prem Gold and AWS Gold both call `utils.indicators.calculate_indicators`.
- On-prem Serving and AWS restitution both call
  `utils.serving.materialize_serving_tables`.
- `jobs/gold-indicators/aws.py` reads Silver Parquet from S3, writes analytical
  Gold Parquet, then writes `trading_gold.*` Parquet datasets.
- `infra/aws/batch` already uploads:
  - `jobs/gold-indicators/aws.py`;
  - zipped `jobs/utils`;
  - zipped `jobs/serving-datamart/registry.py`;
  - SQL files under `jobs/serving-datamart/sql`.
- The Glue job already passes SQL files with `--extra-files` and Python zips
  with `--extra-py-files`.

Decision:

- Keep `jobs/gold-indicators/aws.py` as the AWS batch entry point for the
  existing Gold/restitution path.
- Do not use ECR images for Glue Spark in the next implementation. Glue should
  run Python scripts from S3 with `--extra-py-files`.
- Keep `jobs/utils` as the shared Spark transformation/helper layer.
- Keep restitution SQL in `jobs/serving-datamart/sql`; do not duplicate the
  SQL in Terraform or in the AWS entry point.
- Keep PostgreSQL Serving on-premise only. AWS writes restitution datasets as
  Parquet under `trading_gold.*` and exposes them through Glue Catalog/Athena.

Open gap:

- The repo still has no AWS Raw/Bronze/Silver path consuming Kinesis into S3.
  The existing AWS batch path starts from Silver S3. Do not claim a full
  Binance-to-Athena AWS runtime path until that ingestion/lake step is
  implemented and validated.

## Terraform versus CI/CD responsibilities

Terraform owns long-lived infrastructure:

- S3 lake and Athena result buckets;
- Glue databases, tables, roles and jobs;
- Kinesis streams;
- ECR repositories;
- ECS cluster, task definitions, services and IAM;
- CloudWatch log groups required by Glue/ECS.

CI/CD owns build and versioned artifacts:

- build the producer image;
- push the image to ECR with an immutable tag or digest;
- package `jobs/utils`, the Serving registry and SQL files;
- upload Glue scripts and Python/SQL artifacts to S3 with explicit versioned
  keys;
- run unit/static checks before Terraform deployment.

Implementation note:

- The existing `infra/aws/batch` stack currently uploads Glue artifacts from
  the local working tree. That is acceptable for local static preparation, but
  the implementation phase should introduce explicit artifact version inputs
  or keys so Terraform can reference CI-produced artifacts for repeatable
  deployments.

## Implementation split

This cadrage led to the AWS core implementation phase. That implementation is
now prepared statically in the repo. The next phase after the core implementation
is not AWS runtime validation; it is the cadrage of the missing Kinesis -> S3
Raw/Bronze/Silver lake ingestion path.

Phase 2A - Producer/ECR/ECS/Kinesis:

- add `apps/binance-producer/aws.py`;
- add a small Kinesis publisher helper if it keeps the entry point readable;
- add `boto3`/AWS dependency only for the AWS producer path;
- add unit tests for Kinesis record formatting and partition keys;
- add `infra/aws/core` for Kinesis, ECR, ECS/Fargate, IAM and logs;
- document how to build, tag and push the image.

Phase 2B - Glue artifact packaging and batch hardening:

- refine `infra/aws/batch` so Glue artifacts can be referenced through
  explicit versioned S3 keys or a controlled local-dev mode;
- keep `jobs/gold-indicators/aws.py` thin;
- keep `jobs/utils` and Serving SQL as the shared logic;
- add or preserve tests proving no AWS PostgreSQL/RDS target appears.

Do not implement in Phase 2:

- DynamoDB latest metrics;
- API Gateway/Lambda API;
- Streamlit/local dashboard support;
- CloudWatch alarms;
- AWS Budgets;
- AWS PostgreSQL/RDS.

Post-core next phase:

- cadrer how Kinesis records become Raw, Bronze and Silver datasets on S3;
- decide Glue Streaming ETL or another justified AWS processing pattern;
- define IAM, S3 prefixes, checkpoints, partitions, quality checks and tests;
- keep DynamoDB, API Gateway/Lambda, Streamlit, advanced alarms and Budgets out
  of that lake-ingestion cadrage unless a later scope change explicitly adds
  them.

## Acceptance criteria for implementation

Static/local acceptance:

- Producer Kafka path still exists and keeps using `main.py`.
- AWS producer path reuses `normalize_kline`.
- Kinesis record tests prove payload shape, partition key and required fields.
- Terraform for changed AWS stacks passes `terraform fmt -check -recursive`
  and `terraform validate`.
- Static scans show no RDS/PostgreSQL AWS resources.
- Existing unit tests still pass or any skipped Spark tests are reported
  explicitly.
- Documentation states what is implemented, prepared and unproven.

Runtime acceptance, only when AWS access exists:

Runtime acceptance is not the immediate next phase after the core
implementation. It belongs after the selected AWS path has been framed and
implemented, including Kinesis -> S3 Raw/Bronze/Silver.

- ECR image exists and matches the deployed ECS task definition.
- ECS service reaches steady state.
- Producer logs are visible in CloudWatch.
- Kinesis receives records with expected partition keys and payload fields.
- Kinesis -> S3 Raw/Bronze/Silver ingestion runs and produces the expected S3
  datasets.
- Glue batch job runs successfully from the configured artifact keys.
- Gold and `trading_gold` Parquet outputs appear in S3.
- Glue Catalog tables are visible.
- At least one Athena query succeeds.

## Validation in this cadrage phase

Validated statically:

- Required phase docs were read.
- The pasted attachment matches the existing `docs/aws-phase-prompts.md`
  content by line comparison.
- Producer, contract, AWS Gold entry point, shared utils, Serving SQL and
  Terraform batch files were inspected directly.
- No CI workflow directory was found in the repo.
- No implementation files or Terraform resources were changed in this phase.

Not validated:

- No unit tests were run because this phase changed documentation only.
- No Terraform validation was run because Terraform files were not changed.
- No AWS runtime check was run because credentials are not available in this
  environment.
