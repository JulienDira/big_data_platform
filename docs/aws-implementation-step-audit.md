# AWS implementation step audit

Phase: Phase 9 - static end-to-end AWS implementation verification.

Date: 2026-07-03.

This audit is static and local only. It did not run AWS runtime checks,
`terraform apply`, Glue jobs, ECS tasks, Kinesis producers, Kinesis
`put-record`, Athena data queries, Streamlit Cloud deployment or any AWS
service startup.

## Scope and severity

Severity scale used in this audit:

- `blocking`: prevents the next AWS deployment/runtime phase.
- `important`: needs targeted remediation before the next AWS
  deployment/runtime phase unless explicitly accepted.
- `minor`: non-blocking cleanup, documentation or proof gap.
- `accepted tradeoff`: project-consistent choice with a known limitation.

The audit followed the required flow order:

1. Producer and `infra/aws/core`.
2. Kinesis to Raw S3.
3. Bronze and Silver S3.
4. Gold and `trading_gold` restitution.
5. Serving, API, dashboard and observability.
6. CI/CD, artifacts and deployment preparation.

## References consulted

Official primary references:

- AWS Well-Architected Data Analytics Lens:
  <https://docs.aws.amazon.com/wellarchitected/latest/analytics-lens/analytics-lens.html>
- Amazon ECS best practices:
  <https://docs.aws.amazon.com/AmazonECS/latest/developerguide/ecs-best-practices.html>
- Kinesis Data Streams producer guidance:
  <https://docs.aws.amazon.com/streams/latest/dev/developing-producers-with-sdk.html>
- Amazon ECR tag immutability:
  <https://docs.aws.amazon.com/AmazonECR/latest/userguide/image-tag-mutability.html>
- AWS Glue best practices:
  <https://docs.aws.amazon.com/prescriptive-guidance/latest/serverless-etl-aws-glue/best-practices.html>
- AWS Lambda best practices:
  <https://docs.aws.amazon.com/lambda/latest/dg/best-practices.html>
- API Gateway security best practices:
  <https://docs.aws.amazon.com/apigateway/latest/developerguide/security-best-practices.html>
- DynamoDB design best practices:
  <https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/best-practices.html>
- IAM security best practices:
  <https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html>
- CloudWatch recommended alarms:
  <https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Best_Practice_Recommended_Alarms_AWS_Services.html>
- GitHub OIDC for AWS:
  <https://docs.github.com/en/actions/how-tos/secure-your-work/security-harden-deployments/oidc-in-aws>
- `aws-actions/configure-aws-credentials`:
  <https://github.com/aws-actions/configure-aws-credentials>
- Terraform language style guide:
  <https://developer.hashicorp.com/terraform/language/style>

No community article was needed as a decision source.

## Step audit table

| Step | Files inspected | Static evidence | Result |
|---|---|---|---|
| Producer and AWS core | `apps/binance-producer/main.py`, `aws.py`, `common.py`, `model.py`, `avro_codec.py`, `Dockerfile`, `requirements-aws.txt`, `contracts/market-candle/v1.avsc`, `infra/aws/core`, `.github/workflows/aws-deploy.yml`, `tests/test_producer_aws.py` | Kafka and Kinesis entry points are separate. Both reuse `fetch_latest`, `build_partition_key` and `normalize_kline`. AWS records use canonical Avro binary payloads and `symbol|interval` partition keys. `infra/aws/core` owns Kinesis, ECR, ECS/Fargate, IAM and producer logs. ECR is immutable and scans on push. ECS desired count defaults to `0`. | Conformant after the Kinesis partial-failure fix below. |
| Kinesis to Raw S3 | `jobs/raw-consumer/aws.py`, `jobs/utils/bronze.py`, `infra/aws/batch/glue_job.tf`, `infra/aws/batch/glue_catalog.tf`, `infra/aws/batch/variables.tf`, `tests/test_utils_transforms.py` | Raw Glue Streaming reads Kinesis at the edge, writes append-only Parquet, preserves stream name, partition key, sequence number, arrival timestamp, binary value and ingestion metadata. `is_avro_decodable` is derived from the `from_avro` output being non-null. Checkpoint and output prefixes are Terraform-driven. | Conformant. AWS runtime proof remains missing. |
| Bronze and Silver S3 | `jobs/bronze-ingestion/aws.py`, `jobs/silver-transformation/aws.py`, `jobs/utils/bronze.py`, `jobs/utils/silver.py`, `jobs/utils/quality.py`, `jobs/utils/market_schema.py`, `infra/aws/batch`, `tests/test_utils_transforms.py` | Bronze now reads Raw S3 as a Glue Streaming file source with an explicit Raw schema, decodes Avro and writes valid/rejected Parquet outputs with separate checkpoints. Silver stays batch, reuses `build_silver`, filters closed/valid candles and deduplicates by `(symbol, interval, open_time)` with latest `ingested_at` and `event_id` tie-break. Spark sessions and S3 paths stay in entry points. | Conformant. Local invalid-Avro rejection still depends on the `spark-avro` classpath. AWS runtime proof remains missing. |
| Gold and `trading_gold` restitution | `jobs/gold-indicators/aws.py`, `jobs/utils/indicators.py`, `jobs/utils/serving.py`, `jobs/serving-datamart/registry.py`, `jobs/serving-datamart/sql`, `infra/aws/batch/glue_catalog.tf`, `tests/test_gold_restitution_golden.py`, `tests/test_serving_registry.py`, `tests/test_serving_transformations.py` | Gold AWS reads Silver S3, calculates indicators through shared `calculate_indicators`, writes `gold.market_indicators`, then materializes `trading_gold.*` from the shared SQL registry. Terraform catalogs Gold and restitution Parquet tables for Athena. | Conformant. AWS Glue/Athena runtime proof remains missing. |
| Serving, API, dashboard and observability | `apps/aws-serving-api`, `apps/streamlit-dashboard`, `infra/aws/serving`, `tests/test_aws_serving_api.py`, `tests/test_streamlit_dashboard_boundaries.py` | DynamoDB is a latest cache only. API handlers are read-only, validate fixed symbols/intervals, build bounded Athena queries from fixed table/field sets and do not import Spark or indicator helpers. Projection writes are isolated in `projection_handler.py`. Streamlit uses Cognito/API Gateway through `requests`, not AWS SDK clients. Terraform declares Cognito JWT authorizer, Lambda/API logs, simple alarms and optional Budget notifications. | Conformant. Runtime auth/API/dashboard/alarms/Budget proof remains missing. |
| CI/CD, artifacts and deployment preparation | `.github/workflows/aws-deploy.yml`, `infra/scripts/package-aws-artifacts.py`, `infra/aws/core`, `infra/aws/batch`, `infra/aws/serving`, AWS module READMEs, `tests/test_aws_artifact_packaging.py`, `tests/test_aws_deploy_workflow.py`, `docs/aws-cicd-deployment-cadrage.md` | Pull requests validate only. Non-PR runs use GitHub OIDC, publish image/Glue/Lambda artifacts with `${github.sha}`, and pass explicit artifact references to Terraform. Runtime remains disabled by Terraform inputs: producer desired count `0`, no Glue job start command, projection schedule disabled and no Streamlit deploy. | Conformant as deployment preparation code. GitHub/AWS execution proof remains missing. |

## Blocking findings

None after the correction below.

## Important findings

1. Corrected - Kinesis `PutRecords` partial failures were detected but not
   retried.

   Evidence before correction:

   - `apps/binance-producer/aws.py` raised on any non-zero
     `FailedRecordCount`.
   - AWS Kinesis producer guidance says `PutRecords` can partially fail and
     unsuccessful records should be included in a subsequent request.

   Minimal remediation applied:

   - `publish_records` now retries only failed Kinesis records with bounded
     attempts and simple backoff.
   - `tests/test_producer_aws.py` now covers retrying only the failed record
     and raising after bounded retries.

   Severity after fix: no longer blocking or important.

2. Remaining runtime proof is missing for every AWS service.

   Evidence:

   - No AWS account/runtime validation was used in this phase.
   - `docs/phase-handoff.md` already marks AWS runtime proof as missing.

   Impact: not a static implementation blocker. It must stay explicit before
   the next AWS deployment/runtime phase.

## Minor findings and accepted tradeoffs

- Accepted tradeoff: `apps/binance-producer/Dockerfile` keeps the local Kafka
  `main.py` as its default `CMD`, while `infra/aws/core/main.tf` overrides the
  ECS command to run `aws.py`. This preserves local/on-prem behavior and keeps
  AWS selection at the ECS edge.
- Accepted tradeoff: `infra/aws/batch` keeps
  `upload_glue_artifacts_from_workspace` as a local-dev fallback, while CI uses
  immutable S3 artifact keys and sets it to `false`.
- Minor proof gap: Bronze invalid direct Avro rejection has local test coverage
  guarded by Spark availability, but the direct Avro rejection test is skipped
  when the local Spark classpath lacks the `spark-avro` package.

## Minimal fixes applied

- `apps/binance-producer/aws.py`: added extraction of failed `PutRecords`
  entries, bounded retries and retry logging.
- `tests/test_producer_aws.py`: added tests for partial-failure retry and
  bounded retry failure.

No Terraform resources, AWS services, public APIs, schemas, lake paths or
dashboard behavior were added.

## Validation results

Commands run:

```powershell
git status --short --untracked-files=all
powershell -ExecutionPolicy Bypass -File .\platform.ps1 test
terraform fmt -check -recursive infra/aws
terraform -chdir=infra/aws/core init -backend=false -input=false
terraform -chdir=infra/aws/core validate
terraform -chdir=infra/aws/batch init -backend=false -input=false
terraform -chdir=infra/aws/batch validate
terraform -chdir=infra/aws/serving init -backend=false -input=false
terraform -chdir=infra/aws/serving validate
rg -n "aws_db|aws_rds|postgres|postgresql" infra/aws -g "*.tf"
rg -n "boto3|botocore|aioboto3|awswrangler|s3fs" apps/streamlit-dashboard
rg -n "SparkSession|pyspark|calculate_indicators|rolling|ewm" apps/aws-serving-api
rg -n "AWS_ACCESS_KEY_ID|AWS_SECRET_ACCESS_KEY|aws-access-key-id|aws-secret-access-key|secrets\." .github/workflows/aws-deploy.yml
rg -n "start-job-run|update-service --desired-count|put-record|put-records|streamlit deploy" .github/workflows/aws-deploy.yml
git diff --check
```

Results:

- Initial `git status --short --untracked-files=all` showed pre-existing
  modified docs: `cadrage.md`, `docs/aws-phase-prompts.md`,
  `docs/aws-service-iam-decisions.md` and `docs/phase-handoff.md`.
  They were preserved and not reverted.
- First `platform.ps1 test` attempt failed on Docker access:
  `C:\Users\julie\.docker\config.json: Access is denied` and Docker pipe
  access denied.
- The same `platform.ps1 test` command succeeded after approved Docker access:
  42 tests OK, 1 skipped because local Spark lacks the `spark-avro` package.
- `terraform fmt -check -recursive infra/aws`: passed.
- First Terraform provider initialization attempts for `core`, `batch` and
  `serving` failed in the sandbox because access to `registry.terraform.io`
  was blocked.
- `terraform -chdir=infra/aws/core init -backend=false -input=false`,
  `terraform -chdir=infra/aws/batch init -backend=false -input=false` and
  `terraform -chdir=infra/aws/serving init -backend=false -input=false`
  succeeded after approved provider-initialization network access.
- `terraform -chdir=infra/aws/core validate`: passed.
- `terraform -chdir=infra/aws/batch validate`: passed.
- `terraform -chdir=infra/aws/serving validate`: passed.
- Forbidden AWS PostgreSQL/RDS Terraform scan: no match.
- Forbidden direct AWS SDK imports in Streamlit scan: no match.
- API/Lambda Spark or indicator calculation scan: no match.
- Workflow long-lived AWS key scan: no match.
- Workflow forbidden runtime command scan: no match.
- `git diff --check`: passed. Git printed LF/CRLF normalization warnings for
  modified files on Windows.

Not run:

- `terraform plan`;
- `terraform apply`;
- AWS CLI runtime checks;
- ECS, Kinesis, Glue, S3, Athena, DynamoDB, API Gateway, Lambda, Cognito,
  Streamlit Cloud, CloudWatch alarms or Budget runtime checks.

## Runtime proof still missing

The following remain unproven until a real AWS account and deployment path are
used:

- GitHub OIDC role, GitHub Environment variables and Terraform backend/locking.
- ECR image publication and ECS task image pull.
- ECS producer steady state and Kinesis records.
- Glue Raw Streaming, Bronze Streaming, Silver and Gold job execution.
- Raw/Bronze/Silver/Gold/`trading_gold` S3 outputs.
- Glue Data Catalog visibility and Athena query execution.
- DynamoDB latest projection execution.
- API Gateway/Lambda/Cognito runtime behavior.
- Streamlit Cloud deployment and authentication flow.
- CloudWatch alarms, SNS notifications and AWS Budget visibility.

## Next recommended phase

If the validation commands above pass and no new blocking issue appears,
proceed to Phase 10 - AWS automated deployment and runtime validation.

The next phase should first harden and document GitHub/AWS bootstrap with
GitHub Actions OIDC and a scoped AWS role, then deploy and run controlled AWS
runtime validation only when credentials, permissions and required callback/
alert configuration are available.
