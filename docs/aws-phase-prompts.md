# AWS phase prompts

Prompts to hand off the next AWS phases to separate agents. These prompts do
not replace `AGENTS.md`, `cadrage.md`, `docs/phase-handoff.md` or
`docs/phase-template.md`; they point agents to those source documents.

## Common instructions for every AWS phase

Use this block at the beginning of every prompt:

```text
You work in:
C:\Users\julie\Documents\M2\Soutenance\Big Data Framework\big_data_streaming\big-data-platform

Before any modification, read:
1. AGENTS.md
2. cadrage.md
3. docs/phase-handoff.md
4. docs/phase-template.md
5. docs/aws-service-iam-decisions.md
6. docs/aws-phase-prompts.md

Then inspect the real repository with git status, rg and direct file reads.
Do not revert existing modified or untracked files.

Permanent constraints:
- keep the on-premise Docker Compose/YARN/HDFS/Hive/PostgreSQL path working;
- keep PostgreSQL on-premise only, do not add RDS/PostgreSQL on AWS;
- keep business transformations in jobs/utils or existing shared helpers;
- keep runtime-specific reads, writes, sessions, IAM and arguments at the edge;
- use jobs/<pipeline-step>/aws.py for AWS entry points when the logical step already exists;
- distinguish implementation, static/local validation and real AWS runtime proof;
- do not claim AWS runtime validation without real checks on AWS services.
```

## Phase 1 prompt - AWS core technical cadrage

```text
Mission:
Produce the technical cadrage for reusing the existing code on the AWS core
path, before implementation.

Context:
The on-premise Silver -> Gold -> Serving path is proven. A minimal Terraform
batch stack exists under infra/aws/batch for S3/Glue/Athena, and
jobs/gold-indicators/aws.py exists for the AWS batch Gold/restitution path.
AWS runtime is not proven because no AWS account/credentials are available.

In scope:
1. Audit the existing producer:
   - apps/binance-producer/main.py
   - apps/binance-producer/model.py
   - apps/binance-producer/Dockerfile
   - contracts/market-candle/v1.avsc
   Decide how it should be exploited on AWS:
   - keep shared normalization logic;
   - create a Kinesis adapter/entry point instead of sending Kafka messages;
   - package with ECR;
   - run on ECS/Fargate by default, with EC2 only if a documented FinOps tradeoff justifies it;
   - define IAM, environment variables, logs and tests.
2. Audit the existing Spark/Glue batch path:
   - jobs/gold-indicators/aws.py
   - jobs/utils
   - jobs/serving-datamart/sql
   - infra/aws/batch
   Decide how Glue should run the existing code:
   - scripts and SQL uploaded to S3;
   - jobs/utils packaged as zip and passed with --extra-py-files;
   - Glue arguments and least-privilege IAM;
   - avoid ECR images for Glue Spark unless there is a strong documented reason.
3. Define Terraform vs CI/CD responsibilities:
   - Terraform creates long-lived AWS resources and IAM;
   - CI builds/pushes images and uploads versioned job artifacts where relevant;
   - Terraform references immutable versions or explicit artifact keys.
4. Define the implementation phases and acceptance criteria for the next agent.
5. Update docs/phase-handoff.md with the cadrage result and the next prompt to run.

Out of scope:
- no implementation of the AWS producer, Kinesis, ECS, CI/CD or Glue changes;
- no DynamoDB latest metrics;
- no API Gateway/Lambda API;
- no Streamlit/dashboard work;
- no CloudWatch alarms or AWS Budgets;
- no AWS runtime validation claim.

Expected deliverables:
- a short technical cadrage document, preferably docs/aws-core-portability-cadrage.md;
- updates to docs/phase-handoff.md;
- updates to cadrage.md or AGENTS.md only if a durable rule changes;
- a clear prompt for the next implementation agent.

Validation:
- run documentation scans with rg;
- verify no forbidden Terraform resources were added;
- if no code changed, do not run heavy runtime tests unnecessarily;
- report exactly what was and was not validated.
```

## Phase 2 prompt - AWS core implementation

Run this only after Phase 1 has produced and accepted the cadrage.

```text
Mission:
Implement the AWS core portability path defined by
docs/aws-core-portability-cadrage.md.

In scope, only if confirmed by the cadrage:
- AWS producer adapter/entry point reusing apps/binance-producer/model.py;
- Kinesis Data Streams integration;
- ECR/ECS/Fargate packaging and Terraform;
- Glue/Spark artifact packaging for existing jobs;
- refinements to infra/aws/batch or a new narrowly scoped infra/aws/core module;
- tests for contracts, adapters, Terraform and IAM intent;
- documentation updates.

Out of scope:
- DynamoDB latest metrics;
- API Gateway/Lambda API;
- Streamlit/local dashboard support;
- CloudWatch alarms and AWS Budgets, except basic log groups required by the implemented services;
- RDS/PostgreSQL AWS.

If this phase is too large, split it into:
1. Producer/ECR/ECS/Kinesis implementation.
2. Glue/Spark artifact packaging and lake processing implementation.

Validation:
- run relevant unit/contract tests;
- run terraform fmt and terraform validate for changed Terraform modules;
- run static scans proving no AWS PostgreSQL/RDS target was introduced;
- run terraform plan only if AWS credentials are available;
- do not claim AWS runtime validation without real AWS checks.

End of phase:
- update docs/phase-handoff.md with files changed, commands, exact results,
  proof obtained and proof missing;
- produce the next recommended prompt.
```

## Phase 3 prompt - Kinesis to S3 Raw/Bronze/Silver cadrage

Run this after the AWS core implementation is stable statically. Do not run AWS
runtime validation as the next phase: the Kinesis -> S3 Raw/Bronze/Silver lake
ingestion path is still missing.

```text
Mission:
Frame the missing AWS lake ingestion path from Kinesis to S3 Raw/Bronze/Silver
before implementation.

Context:
The producer can publish canonical market candle Avro records to Kinesis, and
the AWS batch Gold job can read Silver Parquet from S3. The missing link is the
AWS ingestion/lake path that consumes Kinesis and produces Raw, Bronze and
Silver datasets on S3.

In scope:
- audit current on-prem Raw, Bronze and Silver jobs and shared helpers;
- define the AWS Raw layer contract on S3, including envelope, metadata,
  partitions, checkpoints and error/decode status;
- define the AWS Bronze decoding and technical validation path;
- define the AWS Silver typed/deduplicated closed-candle output expected by
  `jobs/gold-indicators/aws.py`;
- choose Glue Streaming ETL or another justified AWS processing pattern;
- define IAM, S3 prefixes, checkpoints, logs, costs and static/local tests;
- decide which logic belongs in `jobs/utils` and which code stays in AWS entry
  points or IO adapters;
- update docs/phase-handoff.md with the next implementation prompt.

Out of scope:
- implementation;
- DynamoDB latest metrics;
- API Gateway/Lambda API;
- Streamlit/dashboard work;
- advanced CloudWatch alarms or AWS Budgets;
- full AWS runtime validation;
- RDS/PostgreSQL AWS.

Expected deliverables:
- a short cadrage document, preferably docs/aws-lake-ingestion-cadrage.md;
- update docs/aws-service-iam-decisions.md statuses;
- update docs/phase-handoff.md with the next implementation prompt;
- update cadrage.md only if the phase order or architecture rules changed.
```

## Phase 4 prompt - Avro Kinesis to S3 Raw/Bronze/Silver implementation

Run this only after Phase 3 has produced and accepted the lake ingestion
cadrage.

```text
Mission:
Implement the AWS lake ingestion path defined by
docs/aws-lake-ingestion-cadrage.md.

In scope, only if confirmed by the cadrage:
- AWS entry points/adapters for Avro Kinesis -> Raw S3;
- Bronze Avro decoding and technical validation to S3;
- Silver typed/deduplicated closed-candle output to S3;
- required Terraform/IAM/S3/log/checkpoint resources;
- packaging for Glue Streaming ETL or the chosen processing service;
- unit/static tests and contract tests;
- documentation updates.

Out of scope:
- DynamoDB latest metrics;
- API Gateway/Lambda API;
- Streamlit/local dashboard support;
- advanced CloudWatch alarms and AWS Budgets;
- RDS/PostgreSQL AWS;
- claiming AWS runtime validation without real AWS checks.

End of phase:
- update docs/phase-handoff.md with exact validations and missing runtime proof;
- produce the next cadrage prompt for restitution/API/observability.
```

## Phase 5 prompt - Restitution, API and observability cadrage

Run this after the AWS core producer path and the Kinesis -> S3
Raw/Bronze/Silver path are implemented at least statically.

```text
Mission:
Frame the later AWS restitution, API, dashboard and observability scope before
implementation.

In scope:
- DynamoDB latest metrics as a cache/projection only, not the historical source of truth;
- API Gateway/Lambda API responsibilities and IAM;
- Streamlit/local dashboard support and its data access mode;
- CloudWatch logs, alarms and AWS Budgets;
- cost controls, lifecycle and cleanup rules;
- tests, runtime proof plan and implementation split.

Out of scope:
- implementation;
- changes to producer/Kinesis/Glue/lake ingestion unless required as documented dependencies;
- RDS/PostgreSQL AWS;
- full AWS runtime validation.

Expected deliverables:
- a short cadrage document, preferably docs/aws-serving-observability-cadrage.md;
- update docs/aws-service-iam-decisions.md statuses;
- update docs/phase-handoff.md with the next implementation prompt.
```

## Phase 6 prompt - Restitution, API and observability implementation

Run this only after Phase 5 has produced and accepted the cadrage.

```text
Mission:
Implement the AWS restitution, API, dashboard support and observability scope
defined by docs/aws-serving-observability-cadrage.md.

In scope, only if confirmed by the cadrage:
- DynamoDB latest metrics projection;
- API Gateway/Lambda backend;
- Streamlit/local dashboard support;
- CloudWatch alarms and AWS Budgets;
- least-privilege IAM;
- static/local tests and Terraform validation.

Out of scope:
- RDS/PostgreSQL AWS;
- replacing S3/Glue/Athena as the historical analytical source;
- claiming AWS runtime validation without real AWS checks.

End of phase:
- update docs/phase-handoff.md with exact validations and missing runtime proof;
- if the selected AWS path is fully developed, prepare the runtime validation
  phase prompt.
```

## Optional phase 7 prompt - AWS runtime validation

```text
Mission:
Validate the fully framed and implemented AWS path in a real AWS account.

Prerequisite:
AWS credentials and permissions are available.
The selected AWS path has already been framed and implemented: producer/ECS/
Kinesis, Kinesis -> S3 Raw/Bronze/Silver, Glue Gold/trading_gold, and any later
API/dashboard/observability surfaces included in the scope.

In scope:
- terraform plan/apply for implemented modules;
- producer/Kinesis/ECS checks;
- Kinesis -> S3 Raw/Bronze/Silver checks;
- Glue job runs;
- S3 Parquet outputs;
- Glue Catalog tables;
- Athena queries;
- DynamoDB/API/dashboard/CloudWatch/Budgets only if implemented;
- cleanup/cost-control verification.

Out of scope:
- new feature implementation;
- claiming success for services that were not actually checked.

End of phase:
- update docs/phase-handoff.md with exact commands, AWS evidence, failures,
  cleanup status and remaining proof gaps.
```
