# AWS static quality audit

Phase: static quality, standards and conformance audit of the current AWS
implementation.

Date: 2026-07-02.

This audit is documentation, code review, static validation and local unit
validation only. It did not run `terraform plan`, `terraform apply`, AWS CLI
runtime checks, real Glue jobs, ECS tasks, Kinesis producers, deployed API
Gateway/Lambda endpoints, Cognito flows, Streamlit Cloud deployment or AWS
Budgets runtime checks.

## Official references consulted

- AWS Well-Architected Data Analytics Lens:
  <https://docs.aws.amazon.com/wellarchitected/latest/analytics-lens/analytics-lens.html>
- AWS Glue best practices:
  <https://docs.aws.amazon.com/prescriptive-guidance/latest/serverless-etl-aws-glue/best-practices.html>
- AWS Lambda best practices:
  <https://docs.aws.amazon.com/lambda/latest/dg/best-practices.html>
- API Gateway security best practices:
  <https://docs.aws.amazon.com/apigateway/latest/developerguide/security-best-practices.html>
- DynamoDB partition key best practices:
  <https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/bp-partition-key-design.html>
- Terraform language style guide:
  <https://developer.hashicorp.com/terraform/language/style>
- Streamlit Community Cloud secrets management:
  <https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management>

Provider guidance used for this audit:

- develop and test Glue jobs locally before AWS execution;
- partition analytical datasets by query patterns and use Parquet/columnar
  storage;
- keep Lambda clients/configuration reusable, use environment variables and
  least-privilege IAM;
- rely on API Gateway logging and CloudWatch alarms for API observability;
- design DynamoDB keys from access patterns and watch for uneven partition
  activity;
- keep Terraform variables typed/described and run `fmt`/`validate`;
- keep Streamlit secrets out of Git and access AWS data through the API.

## Decision

No blocking static non-conformity remains after this phase.

The current AWS implementation is conformant enough for the next CI/CD and
deployment preparation phase. Runtime AWS validation still requires automated
artifact publication and reproducible deployment preparation first.

This is not AWS runtime proof. The AWS path remains statically and locally
validated only.

## Corrected findings

1. Important - projection Lambda depended on API handler internals.

   Before this phase, the projection handler reused Athena helpers by importing
   them from `api_handler.py`. That kept the projection code physically
   separate, but created an avoidable dependency from the write projection to
   the read API handler.

   Correction:
   - shared AWS/Athena helpers now live in `apps/aws-serving-api/serving_common.py:91`;
   - `start_athena_query`, `wait_for_athena_query` and `get_athena_page` are
     shared helpers in `apps/aws-serving-api/serving_common.py:253`;
   - `apps/aws-serving-api/projection_handler.py:8` imports from
     `serving_common`, not from `api_handler`;
   - `tests/test_aws_serving_api.py:143` protects that boundary.

   Impact: the API read handler and latest-metrics projection remain separate
   while sharing neutral infrastructure helpers.

2. Important - synchronous custom CloudWatch metric widened Lambda IAM.

   Before this phase, API/projection code could publish a custom
   `AthenaQueryFailure` metric, requiring `cloudwatch:PutMetricData` with a
   wildcard resource. Lambda and API Gateway already expose native error and
   5xx metrics, and provider guidance favors CloudWatch alarms over synchronous
   metric publishing from handler code for this POC.

   Correction:
   - Lambda code no longer calls `put_metric_data`;
   - `infra/aws/serving/iam.tf` no longer grants `cloudwatch:PutMetricData`;
   - the custom `AthenaQueryFailure` alarm was removed;
   - native alarms remain for API Gateway, Lambda, DynamoDB, Kinesis and ECS in
     `infra/aws/serving/monitoring.tf:19`;
   - `infra/aws/serving/outputs.tf:36` now exports only existing alarm names;
   - `tests/test_aws_serving_api.py:153` and `tests/test_contract.py:69`
     protect the cleanup.

   Impact: IAM is narrower and observability remains covered by native service
   metrics and existing alarms.

3. Minor - Gold AWS duplicated Glue/runtime option parsing.

   `jobs/gold-indicators/aws.py` kept local `option` and `list_option`
   helpers while Raw, Bronze and Silver AWS entry points used
   `jobs/utils/aws_args.py`.

   Correction:
   - `jobs/utils/aws_args.py:7` remains the shared option parser;
   - `jobs/utils/aws_args.py:25` now provides `list_option`;
   - `jobs/gold-indicators/aws.py:15` imports the shared helpers.

   Impact: AWS entry point argument parsing has one shared helper.

## Remaining important findings

1. AWS runtime proof is still missing.

   Evidence:
   - `docs/phase-handoff.md` states that no AWS account/credentials are
     currently available for runtime validation.
   - `docs/aws-service-iam-decisions.md` keeps producer, lake ingestion,
     Glue/Athena, DynamoDB/API/Cognito/Streamlit and observability surfaces as
     `Prepare`, with runtime proof missing.

   Required before claiming runtime validation: deploy and check ECS/Kinesis,
   Glue Raw/Bronze/Silver, S3 outputs, Glue Gold, `trading_gold`, Glue Catalog,
   Athena, DynamoDB projection, API Gateway/Lambda, Cognito, Streamlit Cloud,
   alarms and Budget in a real AWS account.

2. CI/CD and immutable artifact publication remain outside this static phase.

   Evidence:
   - `docs/aws-service-iam-decisions.md` still marks CI/CD as
     `A developper`;
   - `infra/aws/core/README.md` still documents manual image build/push for
     now;
   - `infra/aws/batch` still supports local-dev artifact upload for static
     preparation.

   Impact: not blocking for static conformance, but blocking before global AWS
   runtime validation. Runtime proof should not start until immutable
   image/Glue/Lambda artifact publication is automated.

3. Bronze invalid direct Avro rejection remains classpath-dependent locally.

   Evidence:
   - `powershell -ExecutionPolicy Bypass -File .\platform.ps1 test` passed with
     one skipped test: Spark Avro package is not available in the local test
     classpath.

   Impact: acceptable for local static validation. The guarded test should be
   executed in an environment where `org.apache.spark:spark-avro` is available,
   such as the configured submit path or Glue runtime.

## Conformities observed

1. AWS medallion path is readable and phase-aligned.

   Evidence:
   - `apps/binance-producer/aws.py` publishes Kinesis records using canonical
     Avro payloads and `symbol|interval` partition keys;
   - `jobs/raw-consumer/aws.py`, `jobs/bronze-ingestion/aws.py` and
     `jobs/silver-transformation/aws.py` keep AWS entry points in the existing
     logical job folders;
   - `jobs/gold-indicators/aws.py` reads Silver S3 and writes Gold plus
     `trading_gold` Parquet datasets.

2. Shared transformations stay reusable and environment details stay at the
   edge.

   Evidence:
   - `jobs/utils/bronze.py` contains Avro decode and Bronze valid/rejected
     transformations;
   - `jobs/utils/silver.py` contains the Silver quality/dedup/select logic;
   - `jobs/utils/serving.py` materializes restitution tables from shared SQL;
   - Spark sessions, S3 paths, Kinesis stream names and write modes stay in
     entry points or small IO helpers.

3. API and projection responsibilities are separated.

   Evidence:
   - `apps/aws-serving-api/api_handler.py` exposes read-only routes for health,
     latest metrics, history, signals and daily summaries;
   - `apps/aws-serving-api/projection_handler.py` is the only Lambda handler
     that writes latest metrics to DynamoDB;
   - `rg -n "SparkSession|pyspark|calculate_indicators|rolling|ewm"
     apps/aws-serving-api` returned no match.

4. Streamlit uses API Gateway and Cognito-facing configuration only.

   Evidence:
   - `apps/streamlit-dashboard/app.py` reads configuration through
     `st.secrets` or environment variables;
   - it calls API paths through `requests`;
   - `rg -n "boto3|botocore|aioboto3|awswrangler|s3fs"
     apps/streamlit-dashboard` returned no match.

5. Terraform is modular enough for the current scope.

   Evidence:
   - `infra/aws/core` owns producer/Kinesis/ECR/ECS;
   - `infra/aws/batch` owns lake S3, Glue jobs, Glue Catalog and Athena;
   - `infra/aws/serving` owns DynamoDB, Lambda/API, Cognito, alarms and Budget;
   - `terraform fmt -check -recursive infra/aws` passed;
   - Terraform variables are typed and described in the inspected modules.

6. RDS/PostgreSQL AWS remains absent.

   Evidence:
   - `rg -n "aws_db|aws_rds|postgres|postgresql" infra/aws -g "*.tf"`
     returned no match.

## Validation results

Commands run:

```powershell
git status --short --untracked-files=all
powershell -ExecutionPolicy Bypass -File .\platform.ps1 test
terraform fmt -check -recursive infra\aws
terraform -chdir=infra\aws\core validate
terraform -chdir=infra\aws\batch validate
terraform -chdir=infra\aws\serving validate
rg -n "aws_db|aws_rds|postgres|postgresql" infra\aws -g "*.tf"
rg -n "boto3|botocore|aioboto3|awswrangler|s3fs" apps\streamlit-dashboard
rg -n "SparkSession|pyspark|calculate_indicators|rolling|ewm" apps\aws-serving-api
git diff --check
```

Results:

- `git status --short --untracked-files=all`: working tree was already dirty
  before this phase, with modified documentation files. No existing change was
  reverted.
- First direct `python -m unittest ...` attempt failed because the WindowsApps
  Python launcher could not create the process.
- First `platform.ps1 test` attempt failed on Windows Docker access:
  `C:\Users\julie\.docker\config.json: Access is denied` and
  `//./pipe/docker_engine: Access is denied`.
- `platform.ps1 test` rerun with elevated Docker access succeeded:
  35 tests OK, 1 skipped because local Spark lacks `spark-avro`.
- `terraform fmt -check -recursive infra\aws`: passed.
- `terraform -chdir=infra\aws\core validate`: passed.
- `terraform -chdir=infra\aws\batch validate`: passed.
- `terraform -chdir=infra\aws\serving validate`: passed.
- Forbidden AWS PostgreSQL/RDS scan: no match.
- Forbidden direct AWS SDK imports in Streamlit scan: no match.
- Lambda/API Spark or indicator calculation scan: no match.
- `git diff --check`: passed. Git printed LF/CRLF normalization warnings for
  modified files on Windows.

Not run:

- `terraform plan`;
- `terraform apply`;
- AWS CLI runtime checks;
- ECS, Kinesis, Glue, S3, Athena, DynamoDB, API Gateway, Lambda, Cognito,
  Streamlit Cloud, CloudWatch alarms or Budget runtime checks.

## Recommendation

Proceed to the CI/CD and automated deployment cadrage/implementation path
before any global AWS runtime validation.

Use `Phase 8 prompt - AWS CI/CD and artifact deployment implementation` in
`docs/aws-phase-prompts.md`.

Global runtime validation should be recommended only after immutable ECR, Glue
and Lambda artifacts are published by CI/CD, Terraform consumes those versions,
and the dev/POC deployment preparation path is reproducible. Do not claim AWS
runtime validation from the static results above.
