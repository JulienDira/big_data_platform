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
- prepare the static end-to-end implementation verification prompt, not AWS
  deployment preparation or global runtime validation.
```

## Phase 9 prompt - Static end-to-end AWS implementation verification

Run this after Phase 8 has implemented CI/CD and immutable artifact
publication. This phase is a static code, Terraform, workflow and documentation
verification phase only. It must not run AWS runtime validation or deploy
anything.

```text
Mission:
Verify the AWS implementation end to end, step by step through the data flow,
against the project cadrage, repo rules, current provider best practices and
well-accepted engineering practices. Start with the producer and its AWS
infrastructure, finish only after every implemented AWS step has been checked.

This is an audit and narrow remediation phase. Do not start runtime services.
Do not run terraform apply. Do not run Glue jobs, ECS tasks, Kinesis producers,
Streamlit deployment or AWS CLI runtime checks.

Context:
The AWS implementation is present statically:
- producer/ECR/ECS/Kinesis under apps/binance-producer and infra/aws/core;
- Kinesis -> S3 Raw/Bronze/Silver under jobs/raw-consumer/aws.py,
  jobs/bronze-ingestion/aws.py, jobs/silver-transformation/aws.py,
  jobs/utils and infra/aws/batch;
- Glue Gold and trading_gold restitution under jobs/gold-indicators/aws.py,
  jobs/serving-datamart/sql and infra/aws/batch;
- DynamoDB latest projection, API Gateway/Lambda, Cognito, Streamlit Cloud
  wiring, CloudWatch alarms and Budget under apps/aws-serving-api,
  apps/streamlit-dashboard and infra/aws/serving;
- GitHub Actions OIDC, immutable ECR/S3 artifacts and Terraform artifact
  inputs under .github/workflows, infra/scripts and infra/aws.

Before any change:
1. Read AGENTS.md.
2. Read cadrage.md.
3. Read docs/phase-handoff.md.
4. Read docs/phase-template.md.
5. Read docs/aws-service-iam-decisions.md.
6. Read docs/aws-core-portability-cadrage.md.
7. Read docs/aws-lake-ingestion-cadrage.md.
8. Read docs/aws-serving-observability-cadrage.md.
9. Read docs/aws-cicd-deployment-cadrage.md.
10. Read docs/aws-static-quality-audit.md as historical context, then verify
    the current repo state instead of trusting the old audit.
11. Inspect git status, changed/untracked files, tests, Terraform modules and
    workflow files with rg and direct file reads.
12. Do not revert existing modified or untracked files.

Source requirements:
- Use official primary sources first and cite the exact URLs in the audit doc.
- Use current AWS documentation for Well-Architected/data analytics, ECS/Fargate
  best practices, Kinesis producers, ECR immutability/scanning, Glue, Lambda,
  API Gateway, DynamoDB, IAM least privilege and CloudWatch where relevant.
- Use current GitHub documentation or aws-actions documentation for OIDC and
  workflow permissions.
- Use current Terraform documentation for style, backend, variables and
  validation.
- Community articles, engineering blogs or conference material may be used only
  as secondary context when they clarify an accepted practice. They must not
  override AWS, Terraform, GitHub official documentation or project rules.
- If a source conflicts with the repo cadrage, identify the conflict explicitly
  and recommend the smallest project-consistent correction.

Starter official references to refresh at execution time:
- AWS Well-Architected Data Analytics Lens:
  https://docs.aws.amazon.com/wellarchitected/latest/analytics-lens/analytics-lens.html
- Amazon ECS best practices:
  https://docs.aws.amazon.com/AmazonECS/latest/developerguide/ecs-best-practices.html
- Kinesis Data Streams producer guidance:
  https://docs.aws.amazon.com/streams/latest/dev/developing-producers-with-sdk.html
- Amazon ECR tag immutability:
  https://docs.aws.amazon.com/AmazonECR/latest/userguide/image-tag-mutability.html
- AWS Glue best practices:
  https://docs.aws.amazon.com/prescriptive-guidance/latest/serverless-etl-aws-glue/best-practices.html
- AWS Lambda best practices:
  https://docs.aws.amazon.com/lambda/latest/dg/best-practices.html
- API Gateway security best practices:
  https://docs.aws.amazon.com/apigateway/latest/developerguide/security-best-practices.html
- DynamoDB design best practices:
  https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/best-practices.html
- GitHub OIDC for AWS:
  https://docs.github.com/en/actions/how-tos/secure-your-work/security-harden-deployments/oidc-in-aws
- aws-actions configure-aws-credentials:
  https://github.com/aws-actions/configure-aws-credentials
- Terraform language style guide:
  https://developer.hashicorp.com/terraform/language/style

Verification method:
Work in strict flow order. For each step, finish the local checklist, record
findings, classify risks, and only then move to the next step.

For every step, produce:
- files inspected;
- applicable project rules and external references;
- conformity findings;
- non-conformities or missing proof;
- exact code/Terraform/workflow evidence;
- severity: blocking, important, minor or accepted tradeoff;
- minimal remediation, if needed;
- tests or static scans added or run.

Step 1 - Producer and AWS core infrastructure:
Inspect:
- apps/binance-producer/main.py
- apps/binance-producer/aws.py
- apps/binance-producer/model.py
- apps/binance-producer/avro_codec.py
- apps/binance-producer/Dockerfile
- apps/binance-producer/requirements-aws.txt
- contracts/market-candle/v1.avsc
- infra/aws/core
- relevant .github/workflows/aws-deploy.yml producer image steps

Verify:
- on-prem Kafka producer and AWS Kinesis producer stay separated cleanly;
- shared normalization and Avro contract are reused without duplicated business
  rules;
- Kinesis payload, partition key, batching/retry/error handling and stream
  arguments are explicit and testable;
- Docker image is suitable for ECS/Fargate, contains no secrets and installs AWS
  dependencies only for the AWS path;
- ECS task definition, task role, execution role, logs, desired count default,
  VPC/subnet inputs and Kinesis IAM are least privilege and readable;
- ECR immutability/scanning and CI image tagging match the artifact strategy;
- no RDS/PostgreSQL AWS target or unrelated service drift appears.

Step 2 - Kinesis to Raw S3:
Inspect:
- jobs/raw-consumer/aws.py
- jobs/utils used by Raw
- infra/aws/batch Glue Raw job, IAM, S3 prefixes, checkpoints and logs
- tests covering Raw/Kinesis behavior

Verify:
- Raw preserves the source envelope and technical metadata;
- Avro framing/decoding responsibility is at the edge;
- checkpoint, temp, rejected/error and partition choices are explicit;
- Glue Streaming configuration is minimal and tied to the cadrage;
- IAM is scoped to Kinesis read, target S3 prefixes and required logs only.

Step 3 - Bronze and Silver S3:
Inspect:
- jobs/bronze-ingestion/aws.py
- jobs/silver-transformation/aws.py
- jobs/utils/bronze.py
- jobs/utils/silver.py
- related schemas, quality helpers and tests
- infra/aws/batch Bronze/Silver Glue jobs, S3 prefixes and IAM

Verify:
- Bronze decodes payloads and applies first technical validity checks;
- Silver keeps clean, typed, deduplicated closed candles;
- transformations remain DataFrame-in/DataFrame-out and avoid Spark sessions,
  S3 paths, Glue arguments or IAM details;
- rejected/invalid records and replay/idempotency behavior are clear;
- partitions and table/catalog assumptions match Gold expectations.

Step 4 - Gold and trading_gold restitution:
Inspect:
- jobs/gold-indicators/aws.py
- jobs/utils/indicators.py
- jobs/utils/serving.py
- jobs/serving-datamart/sql
- infra/aws/batch Gold/catalog/Athena resources and artifact references
- tests covering indicators, SQL registry and AWS Gold constraints

Verify:
- indicators stay in Gold, not in Serving or API code;
- trading_gold.* datasets are materialized as reusable restitution outputs on
  S3/Glue/Athena;
- SQL registry and shared restitution logic are reused instead of duplicated;
- Parquet, partitioning, catalog and Athena assumptions are consistent;
- Terraform consumes CI-published Glue artifacts correctly in CI mode and keeps
  local-dev fallback understandable.

Step 5 - Serving, API, dashboard and observability:
Inspect:
- apps/aws-serving-api
- apps/streamlit-dashboard
- infra/aws/serving
- tests for API/projection/dashboard guardrails

Verify:
- DynamoDB is only a latest-metrics cache/projection, not historical source of
  truth;
- API handlers are read-only, validate inputs, return stable JSON and do not
  compute technical indicators;
- projection writes are separated from API reads;
- Lambda packaging via Zip/S3 and source hash is consistent with Terraform;
- Cognito/API Gateway authorization and CORS variables are explicit;
- Streamlit calls API Gateway only and does not import AWS SDK/data-service
  clients directly;
- CloudWatch alarms, logs, SNS and Budget stay simple and POC-scoped.

Step 6 - CI/CD, artifacts and cross-cutting deployment preparation:
Inspect:
- .github/workflows/aws-deploy.yml
- infra/scripts/package-aws-artifacts.py
- infra/aws/core, infra/aws/batch and infra/aws/serving backend/artifact inputs
- README files for the AWS modules
- docs/aws-cicd-deployment-cadrage.md
- tests/test_aws_artifact_packaging.py
- tests/test_aws_deploy_workflow.py

Verify:
- PR path validates only and cannot publish/apply;
- deployment path uses GitHub OIDC with id-token: write and role assumption,
  not long-lived AWS keys;
- producer image, Glue tree and Lambda zip are versioned by commit SHA;
- Terraform consumes explicit image tags, S3 keys and Lambda source hashes;
- runtime remains disabled by default: ECS desired count 0, no Glue job starts,
  projection schedule disabled and no Streamlit deploy;
- package script layout is deterministic, tested and not hidden in Terraform;
- docs clearly separate implemented, prepared, statically validated and runtime
  unproven states.

Allowed changes:
- Update or create a concise audit document, preferably
  docs/aws-implementation-step-audit.md.
- Add or adjust static/unit tests that directly protect a discovered risk.
- Make minimal code, Terraform or workflow corrections only when the audit finds
  a concrete non-conformity.
- Update docs/phase-handoff.md at the end of the phase.
- Update cadrage.md, AGENTS.md or module READMEs only if the audit changes a
  durable rule or reveals stale documentation.

Out of scope:
- AWS runtime validation;
- terraform plan/apply;
- AWS CLI service checks;
- ECS scale-up or service start;
- Kinesis put-record/put-records against AWS;
- Glue job start;
- Athena data queries in AWS;
- Streamlit Cloud deployment;
- broad rewrites, new frameworks, generic base classes or new top-level AWS job
  trees;
- adding new AWS services or RDS/PostgreSQL AWS.

Expected output document structure:
1. Scope and non-runtime boundary.
2. References consulted, split between official primary sources and secondary
   community/context sources.
3. Step-by-step audit table from producer to CI/CD.
4. Blocking findings.
5. Important findings.
6. Minor findings or accepted tradeoffs.
7. Minimal fixes applied, if any.
8. Validation commands and exact results.
9. Runtime proof still missing.
10. Next recommended phase.

Validation:
- powershell -ExecutionPolicy Bypass -File .\platform.ps1 test
- terraform fmt -check -recursive infra/aws
- terraform -chdir=infra/aws/core init -backend=false then validate, if
  provider initialization is not already available
- terraform -chdir=infra/aws/batch init -backend=false then validate, if
  provider initialization is not already available
- terraform -chdir=infra/aws/serving init -backend=false then validate, if
  provider initialization is not already available
- rg scans proving no AWS RDS/PostgreSQL target
- rg scans proving Streamlit has no direct AWS SDK/data-service clients
- rg scans proving API/Lambda handlers do not import Spark or indicator
  calculation helpers
- rg scans proving the workflow has no long-lived AWS key normal path and no
  forbidden runtime commands
- git diff --check

End of phase:
- if all steps are conformant and only runtime proof is missing, recommend
  Phase 10 - AWS automated deployment and runtime validation;
- if blocking or important static issues remain, recommend one narrow
  remediation phase before deployment/runtime validation;
- update docs/phase-handoff.md with findings, changed files, validation
  results, missing proof and a ready-to-use next-agent prompt.
```

## Phase 10 prompt - AWS automated deployment and runtime validation

Run this after Phase 9 has verified the implementation step by step and no
blocking static issue remains. This phase intentionally combines deployment
hardening, GitHub/AWS bootstrap documentation, automated deployment through
GitHub Actions and controlled AWS runtime validation because the user now wants
the next agent to make the push-to-main path deploy and run the AWS pipeline
end to end.

```text
Mission:
Harden, document and test the AWS deployment path so that, after one-time
GitHub/AWS bootstrap, a push to `main` can validate, publish immutable
artifacts, deploy the dev/POC AWS infrastructure and run a controlled AWS
runtime validation of the implemented data path.

Important stance:
- Do not use a long-lived AWS access key or an administrator IAM user as the
  normal GitHub deployment path, even if it looks simpler.
- Prefer GitHub Actions OIDC, a scoped AWS deploy role, GitHub Environment
  variables/secrets, Terraform remote state and explicit least-privilege IAM.
- If a temporary admin action is needed for one-time bootstrap, document it as
  manual bootstrap only, not as the recurring CI/CD credential model.
- Keep PostgreSQL/RDS out of AWS.
- Keep the runtime validation controlled, observable and cost-bounded.

Before changes:
1. Read `AGENTS.md`.
2. Read `cadrage.md`.
3. Read `docs/phase-handoff.md`.
4. Read `docs/phase-template.md`.
5. Read `docs/aws-service-iam-decisions.md`.
6. Read `docs/aws-phase-prompts.md`.
7. Read `docs/aws-implementation-step-audit.md`.
8. Read `docs/aws-cicd-deployment-cadrage.md`.
9. Inspect the real repo with `git status`, `rg` and direct reads of:
   - `.github/workflows/aws-deploy.yml`;
   - `infra/aws/core`, `infra/aws/batch`, `infra/aws/serving`;
   - `infra/scripts/package-aws-artifacts.py`;
   - `apps/binance-producer`, `apps/aws-serving-api`,
     `apps/streamlit-dashboard`;
   - `jobs/raw-consumer/aws.py`, `jobs/bronze-ingestion/aws.py`,
     `jobs/silver-transformation/aws.py`, `jobs/gold-indicators/aws.py`;
   - tests covering workflow, packaging, producer, API, dashboard and
     transformations.

Source requirements:
- Search current official documentation before deciding or editing.
- Use official AWS, GitHub, Terraform and HashiCorp references as decision
  authorities.
- Use community articles only as secondary context; never let them override the
  repo cadrage or official provider guidance.
- Cite every external URL used in the README or deployment audit.
- Required starter references to refresh:
  - GitHub OIDC for AWS:
    https://docs.github.com/en/actions/how-tos/secure-your-work/security-harden-deployments/oidc-in-aws
  - GitHub Environments:
    https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments
  - GitHub Actions secure use:
    https://docs.github.com/en/actions/security-for-github-actions/security-guides/security-hardening-for-github-actions
  - aws-actions/configure-aws-credentials:
    https://github.com/aws-actions/configure-aws-credentials
  - AWS IAM best practices:
    https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html
  - AWS IAM OIDC provider setup:
    https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_providers_create_oidc.html
  - Terraform automation:
    https://developer.hashicorp.com/terraform/tutorials/automation/automate-terraform
  - Terraform S3 backend:
    https://developer.hashicorp.com/terraform/language/backend/s3
  - AWS Well-Architected Operational Excellence:
    https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/welcome.html
  - AWS/GitHub ECS deployment guidance as context:
    https://docs.github.com/en/actions/how-tos/deploy/deploy-to-third-party-platforms/amazon-elastic-container-service

In scope:
- Audit the current workflow against current DevOps/deployment best practices:
  OIDC, role trust policy, environment protection, minimal permissions,
  immutable artifacts, Terraform automation, state locking, concurrency,
  rollback/retry behavior, logs and cost controls.
- Decide the smallest compliant automation model for this POC:
  `push main -> validate -> publish artifacts -> terraform apply -> controlled
  AWS runtime validation`.
- Implement missing workflow/Terraform/script changes needed for that model if
  the repo does not already support it.
- Add or update focused tests for workflow guardrails, forbidden long-lived
  keys, forbidden RDS/PostgreSQL AWS, runtime job gating and README examples.
- Create a simple deployment README, preferably `infra/aws/README.md`, written
  for a developer who wants to configure GitHub once and then deploy by pushing
  to `main`.
- The README must explain:
  - why the normal path uses GitHub OIDC instead of AWS access keys;
  - how to create or verify the AWS OIDC provider and deploy role;
  - which trust-policy conditions to use for repository, branch or GitHub
    Environment;
  - which GitHub Environment variables/secrets are required;
  - which Terraform backend/locking resources must exist;
  - how the workflow publishes ECR, Glue and Lambda artifacts;
  - how the workflow applies Terraform and triggers the AWS runtime validation;
  - how to read runtime proof from ECS/Kinesis/S3/Glue/Athena/DynamoDB/API;
  - how to stop or clean up runtime resources and control POC cost;
  - what remains manual, if anything.
- If AWS access is available, run the deployment/runtime path and capture exact
  evidence.
- If AWS access, GitHub permissions or bootstrap prerequisites are missing,
  do not fake runtime proof: document the exact blocker, finish the README and
  leave a precise checklist for the missing manual bootstrap.

Runtime validation target, once deployment is possible:
- Terraform plan/apply or GitHub Actions deployment for `core`, `batch` and
  `serving`.
- Producer image exists in ECR and is referenced by the ECS task definition.
- ECS producer can be started intentionally for the validation window.
- Kinesis receives market-candle records.
- Raw Glue Streaming consumes Kinesis and writes Raw S3.
- Bronze and Silver Glue jobs run and write S3 outputs.
- Gold Glue job runs and writes `gold.market_indicators` plus
  `trading_gold.*`.
- Glue Catalog tables exist and match expected databases/tables.
- Athena can query at least one Gold or `trading_gold` table.
- DynamoDB latest projection runs if enabled and writes latest metrics.
- API Gateway/Lambda health and at least one read endpoint work if deployed.
- Cognito/Streamlit proof is checked only if callback URLs and deployment
  context are ready; otherwise document it as still unproven.
- CloudWatch logs/alarms and Budget resources are visible if deployed.

Out of scope:
- Adding new AWS services beyond the existing target stack.
- Introducing RDS/PostgreSQL on AWS.
- Replacing S3/Glue/Athena with another historical source of truth.
- Broad refactors of jobs or Terraform modules.
- Making Streamlit read S3, Athena, DynamoDB or Glue directly.
- Storing `AWS_ACCESS_KEY_ID` or `AWS_SECRET_ACCESS_KEY` as the normal
  GitHub deployment credential path.

Validation commands before or after edits, as applicable:
- `powershell -ExecutionPolicy Bypass -File .\platform.ps1 test`
- `terraform fmt -check -recursive infra/aws`
- `terraform -chdir=infra/aws/core validate`
- `terraform -chdir=infra/aws/batch validate`
- `terraform -chdir=infra/aws/serving validate`
- scans proving no RDS/PostgreSQL AWS target;
- scans proving no long-lived AWS keys in workflows or docs as the normal path;
- scans proving Streamlit still has no direct AWS SDK/data-service access;
- `git diff --check`.

Expected deliverables:
- Updated workflow/Terraform/scripts/tests only if needed to make the
  automated deployment/runtime path standards-compliant.
- `infra/aws/README.md` or an equivalent concise deployment README.
- `docs/phase-handoff.md` updated with changed files, commands, exact AWS
  proof, blockers, cleanup/cost-control state and next recommendation.
- `cadrage.md`, `docs/aws-service-iam-decisions.md` or module READMEs updated
  only if the phase changes a durable rule or makes existing docs stale.

End of phase:
- If runtime succeeds, record exact AWS surfaces checked and recommend a narrow
  stabilization/monitoring or demo-hardening phase.
- If deployment succeeds but runtime fails, recommend one targeted remediation
  phase named after the failing surface.
- If bootstrap is missing, recommend the exact manual bootstrap checklist and
  do not claim AWS runtime validation.
```
