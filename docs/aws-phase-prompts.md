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
- Streamlit Cloud as the default POC dashboard target, plus ECS/Fargate as an AWS-hosted alternative only if needed;
- Amazon Cognito authentication for Streamlit users and API Gateway JWT authorization;
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
- Cognito User Pool, Hosted UI, app client, groups and API Gateway JWT authorizer;
- Streamlit Cloud wiring through API Gateway only, with ECS/Fargate as an optional AWS-hosted alternative if the cadrage requires it;
- CloudWatch alarms and AWS Budgets;
- least-privilege IAM;
- static/local tests and Terraform validation.

Out of scope:
- RDS/PostgreSQL AWS;
- replacing S3/Glue/Athena as the historical analytical source;
- direct Streamlit access to DynamoDB, Athena, S3 or Glue;
- claiming AWS runtime validation without real AWS checks.

End of phase:
- update docs/phase-handoff.md with exact validations and missing runtime proof;
- prepare the static quality and conformance audit prompt before any runtime
  validation phase.
```

## Phase 7 prompt - Static quality, standards and conformance audit

Run this after the AWS producer/lake/Gold/restitution/API/dashboard/
observability implementation is present at least statically, and before any AWS
runtime validation.

```text
Mission:
Audit the static AWS implementation for code quality, architecture conformance,
data engineering practices, software/API practices, DevOps/IaC practices and
provider standards. Apply only minimal refactors when the audit finds concrete
violations of the repo rules or obvious over-complexity.

Context:
The AWS path is implemented statically but not runtime-validated:
- producer/ECS/Kinesis under apps/binance-producer and infra/aws/core;
- Kinesis -> S3 Raw/Bronze/Silver under jobs/raw-consumer/aws.py,
  jobs/bronze-ingestion/aws.py, jobs/silver-transformation/aws.py,
  jobs/utils and infra/aws/batch;
- Glue Gold and trading_gold restitution under jobs/gold-indicators/aws.py,
  jobs/serving-datamart/sql and infra/aws/batch;
- DynamoDB latest metrics, API Gateway/Lambda, Cognito, Streamlit Cloud wiring,
  CloudWatch alarms and Budget under apps/aws-serving-api,
  apps/streamlit-dashboard and infra/aws/serving.

Before changes:
- read AGENTS.md, cadrage.md, docs/phase-handoff.md, docs/phase-template.md,
  docs/aws-service-iam-decisions.md, docs/aws-core-portability-cadrage.md,
  docs/aws-lake-ingestion-cadrage.md and
  docs/aws-serving-observability-cadrage.md;
- read docs/aws-static-quality-audit.md as historical context, then refresh it
  against the current repo state;
- inspect git status, the actual AWS code, Terraform and tests;
- do not revert existing modified or untracked files;
- do not run terraform plan/apply, AWS CLI runtime checks or Streamlit deploy.

Use current primary-source references:
- AWS Well-Architected Data Analytics Lens:
  https://docs.aws.amazon.com/wellarchitected/latest/analytics-lens/analytics-lens.html
- AWS Glue best practices:
  https://docs.aws.amazon.com/prescriptive-guidance/latest/serverless-etl-aws-glue/best-practices.html
- AWS Lambda best practices:
  https://docs.aws.amazon.com/lambda/latest/dg/best-practices.html
- API Gateway security best practices:
  https://docs.aws.amazon.com/apigateway/latest/developerguide/security-best-practices.html
- DynamoDB design best practices:
  https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/best-practices.html
- Terraform language style guide:
  https://developer.hashicorp.com/terraform/language/style
- Streamlit secrets management documentation:
  https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management

In scope:
- verify one source of truth for contracts, paths, table names, partitions,
  symbols, intervals, IAM boundaries and runtime parameters;
- verify job/domain structure stays readable: one logical pipeline step per
  folder, edge-specific aws.py/main.py entry points, shared reusable logic in
  jobs/utils or a small domain helper, not monolithic files;
- verify transformations stay pure and atomic: no SparkSession, S3, Glue,
  DynamoDB, PostgreSQL, API or IAM details inside business transformations;
- verify API/Lambda code is simple, read-only for API handlers, does not compute
  EMA/MACD/RSI/Bollinger, does not write lake datasets, validates parameters,
  returns stable JSON and separates projection writes from API reads;
- verify Streamlit calls API Gateway only and uses Streamlit secrets/config,
  with no AWS SDK or direct DynamoDB/Athena/S3/Glue access;
- verify Terraform follows readable module boundaries, least privilege IAM,
  typed/described variables, consistent naming, no needless variables, no RDS
  or AWS PostgreSQL target, and no broad wildcard permissions unless justified;
- verify data engineering choices: medallion boundaries, partitioning,
  Parquet outputs, Glue Catalog/Athena role, rejected data handling,
  idempotent/replayable batch behavior and explicit proof boundaries;
- verify DevOps choices: artifact ownership, Docker/ECR/ECS separation,
  Terraform vs CI/CD responsibilities, log retention, alarms, Budget and
  secrets handling;
- add or adjust static/unit tests only where they directly protect discovered
  risks;
- refactor only concrete issues found during the audit, keeping changes small,
  domain-oriented and easier to read.

Out of scope:
- AWS runtime validation;
- terraform plan/apply;
- AWS CLI service checks;
- Streamlit Cloud deployment;
- broad rewrites, new frameworks, factories, base classes or generic plugin
  systems;
- changing business semantics unless a failing test or source-of-truth mismatch
  proves the current behavior is wrong;
- adding RDS/PostgreSQL AWS.

Expected output:
- a concise audit result, preferably in docs/aws-static-quality-audit.md or an
  update to that file if it already exists;
- any minimal refactors needed to restore atomicity, purity, readability or
  source-of-truth discipline;
- updated tests for changed behavior or newly protected constraints;
- docs/phase-handoff.md updated with findings, changed files, validation
  results, remaining risks and the next recommended phase.

Validation:
- powershell -ExecutionPolicy Bypass -File .\platform.ps1 test
- terraform fmt -check -recursive infra/aws
- terraform -chdir=infra/aws/core validate
- terraform -chdir=infra/aws/batch validate
- terraform -chdir=infra/aws/serving validate
- rg scans proving no AWS RDS/PostgreSQL target and no direct Streamlit AWS SDK
  access
- rg scans proving Lambda/API handlers do not import Spark or indicator
  calculation helpers
- git diff --check

End of phase:
- if the implementation is conformant and static/local validation passes,
  prepare the CI/CD and deployment preparation prompt as the next phase;
- if major design issues remain, recommend one narrow remediation phase instead
  of runtime validation.
```

## Phase 8 prompt - AWS CI/CD and artifact deployment implementation

Run this after the static quality, standards and conformance audit. Do not run
global AWS runtime validation yet.

```text
Mission:
Implement the simplified AWS CI/CD and deployment preparation path defined in
docs/aws-cicd-deployment-cadrage.md.

Context:
The AWS implementation is prepared statically, but deployment is still too
manual: producer image build/push, Glue artifacts and Lambda package publication
must become reproducible and automated before global runtime validation.

Before changes:
- read AGENTS.md, cadrage.md, docs/phase-handoff.md, docs/phase-template.md,
  docs/aws-service-iam-decisions.md, docs/aws-phase-prompts.md,
  docs/aws-static-quality-audit.md and
  docs/aws-cicd-deployment-cadrage.md;
- inspect git status, .github, infra/aws/core, infra/aws/batch,
  infra/aws/serving, apps/binance-producer, apps/aws-serving-api, jobs and
  tests;
- do not revert existing modified or untracked files;
- do not run global AWS runtime validation.

In scope:
- add a GitHub Actions workflow on push to main and pull_request validation;
- use AWS OIDC with AWS_DEPLOY_ROLE_ARN, not long-lived AWS access keys;
- add or document the bootstrap path for Terraform remote state, locking and
  the GitHub deploy role;
- publish the producer Docker image to ECR with an immutable commit SHA tag;
- publish Glue scripts, jobs-utils.zip, serving-registry.zip, SQL and Avro
  contract under a commit-SHA artifact version;
- publish the Lambda API/projection zip to S3 and pass its key/hash to
  Terraform;
- adjust Terraform inputs so CI consumes immutable artifact references instead
  of building zips from the working tree in CI mode;
- keep runtime disabled by default: ECS desired count 0, no Glue job starts,
  projection schedule disabled unless explicitly enabled later;
- update docs/phase-handoff.md with exact validation results and missing proof.

Out of scope:
- global AWS runtime validation;
- starting ECS/Kinesis runtime;
- running Glue jobs;
- Streamlit Cloud deployment;
- adding RDS/PostgreSQL AWS;
- using Lambda ECR images by default.

Validation:
- run repo static/unit tests if available in the environment;
- run terraform fmt and terraform validate for changed AWS modules;
- run rg scans for forbidden AWS PostgreSQL/RDS and forbidden runtime commands;
- run git diff --check;
- do not run terraform apply unless the phase explicitly has bootstrap and
  deploy permissions and is implementing the dev/POC automation path.

End of phase:
- update docs/phase-handoff.md with the workflow, Terraform/artifact changes,
  validation results, missing runtime proof and the next recommended phase;
- prepare the AWS deployment preparation prompt, not global runtime validation.
```

## Phase 9 prompt - AWS deployment preparation

Run this after Phase 8 has implemented CI/CD and immutable artifact publication.
This phase may apply the prepared dev/POC infrastructure through the automated
path, but it still must not execute the full data runtime.

```text
Mission:
Use the implemented CI/CD path to prepare AWS infrastructure deployment for the
dev/POC environment without claiming global runtime validation.

Prerequisites:
- GitHub OIDC role and Terraform backend/locking bootstrap are configured.
- GitHub Environment variables are present for AWS region, deploy role, VPC,
  subnets, callbacks, CORS origins and optional alert email.
- CI/CD publishes producer, Glue and Lambda artifacts with immutable commit SHA
  versions.

In scope:
- run the automated dev/POC deployment path from GitHub Actions;
- verify Terraform outputs for core, batch and serving modules;
- verify artifact references in task definitions, Glue jobs and Lambda
  functions point to the intended immutable version;
- keep runtime disabled by default: ECS producer desired count 0, no Glue job
  runs, projection schedule disabled unless explicitly enabled, no Streamlit
  Cloud deploy;
- document exact outputs and proof gaps in docs/phase-handoff.md.

Out of scope:
- starting the producer runtime;
- sending Kinesis records;
- running Glue Raw/Bronze/Silver/Gold jobs;
- Athena data validation;
- API/Cognito/Streamlit runtime validation;
- Streamlit Cloud deployment;
- adding new AWS features.

End of phase:
- if deployment preparation is reproducible and no critical gap remains,
  prepare the optional global AWS runtime validation prompt;
- otherwise recommend one narrow CI/CD/deployment remediation phase.
```

## Optional phase 10 prompt - AWS runtime validation

```text
Mission:
Validate the fully framed and implemented AWS path in a real AWS account.

Prerequisite:
AWS credentials and permissions are available.
The selected AWS path has already been framed and implemented: producer/ECS/
Kinesis, Kinesis -> S3 Raw/Bronze/Silver, Glue Gold/trading_gold, and any later
API/dashboard/observability surfaces included in the scope. The static quality,
standards and conformance audit phase has been completed. The CI/CD and
deployment preparation phases have published immutable artifacts and prepared
the dev/POC infrastructure reproducibly.

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
