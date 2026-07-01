# AWS static quality audit

Phase: static quality and conformity audit of previous AWS phases.

Date: 2026-07-01.

This audit is documentation and static validation only. It did not add runtime
features, did not run AWS resources, and did not correct functional code.

## Decision

No blocking static non-conformity was found in the checked repo state.

The AWS core producer/Kinesis/ECS/ECR path, Kinesis -> S3
Raw/Bronze/Silver lake path, and Glue Gold/trading_gold path are coherent with
the current cadrage and are ready for the next cadrage phase:
restitution/API/observability.

This is not AWS runtime proof. The AWS path remains prepared and statically
validated only.

Follow-up implemented on 2026-07-01:

- `apps/binance-producer/avro_codec.py` now delegates Avro binary
  serialization/deserialization to `fastavro` only.
- The previous manual Avro fallback was removed.
- Producer-side invalid Avro payload decoding is covered by unit tests.
- A guarded Bronze test now exercises the invalid direct Avro path when the
  Spark Avro package is available in the local test classpath.

## Blocking findings

None.

No Terraform resource for AWS RDS/PostgreSQL, DynamoDB, Lambda, API Gateway or
Budgets was found in `infra/aws`.

## Important findings

1. AWS runtime proof is still missing.

   Evidence:
   - `docs/aws-service-iam-decisions.md:23` states that AWS producer/lake
     ingestion runtime proof is missing.
   - `docs/aws-service-iam-decisions.md:41-44` marks Glue Streaming,
     S3 writes and Athena execution as prepared but not runtime proven.
   - `docs/aws-service-iam-decisions.md:112-113` keeps AWS as statically
     validated only until real AWS checks are performed.

   Impact: this does not block the next cadrage phase, but it blocks any claim
   that the AWS path is deployed or end-to-end validated.

   Required before AWS runtime validation: deploy and check ECS/Kinesis,
   Glue Streaming, Raw/Bronze/Silver S3, Glue Gold, Glue Catalog and Athena in
   a real AWS account.

2. CI/CD and immutable artifact publication remain missing.

   Evidence:
   - `docs/aws-service-iam-decisions.md:30` keeps CI/CD as `A developper`.
   - `docs/aws-core-portability-cadrage.md:186-189` assigns producer image
     build, ECR push and versioned artifacts to CI/CD.
   - `infra/aws/core/README.md:21-35` documents the image build/push as a
     manual step for now.
   - `infra/aws/batch/main.tf:23-24` has an artifact version variable path, but
     `infra/aws/batch/README.md:24-25` keeps the default `local-dev` path for
     local static validation.

   Impact: not blocking for the next cadrage phase, but blocking for a clean
   repeatable deployment phase.

   Required before runtime-oriented deployment: implement or document the
   selected CI/CD path for immutable producer images and Glue artifacts.

3. Malformed Avro coverage improved, with one remaining local classpath limit.

   Evidence:
   - `apps/binance-producer/avro_codec.py` now uses `fastavro.parse_schema`,
     `fastavro.schemaless_writer` and `fastavro.schemaless_reader`.
   - `tests/test_producer_aws.py` validates positive Avro payload
     encoding/decoding and invalid payload failure for the AWS producer.
   - `tests/test_utils_transforms.py` includes a guarded invalid direct Avro
     Bronze test.
   - Local `platform.ps1 test` skips that Bronze decoder test when the Spark
     Avro package is not available in the local Spark classpath.

   Impact: producer Avro behavior is now covered with `fastavro`. The direct
   Spark `from_avro` rejection path should still be executed in an environment
   where `org.apache.spark:spark-avro` is present, such as the configured
   Spark submit or Glue runtime.

4. Full Glue Schema Registry integration is intentionally deferred and still
   uncadred.

   Evidence:
   - `docs/aws-service-iam-decisions.md:37` keeps the canonical Avro contract
     as prepared and Glue Schema Registry as reported.
   - `docs/aws-core-portability-cadrage.md:62-65` explicitly defers full Glue
     Schema Registry integration.

   Impact: acceptable for the current binary Avro Kinesis scope, but should not
   be described as implemented schema registry governance.

## Minor findings

1. The Athena query role is still a later design item.

   Evidence:
   - `docs/aws-service-iam-decisions.md:64` marks `athena-query-role` as
     `A cadrer`.
   - `docs/aws-service-iam-decisions.md:87` keeps AWS runtime validation on
     S3/Glue/Athena as reported.

   Impact: non-blocking for current static AWS path; to be framed in the
   restitution/API/observability cadrage if an API or dashboard needs query
   access.

2. The runtime proof wording is mostly clear, but future agents must avoid
   treating README runtime commands as audit commands.

   Evidence:
   - `infra/aws/core/README.md:38-43` documents Terraform runtime workflow,
     including `terraform plan`, for a future deployment context.
   - `docs/aws-phase-prompts.md:131-133` and
     `docs/aws-lake-ingestion-cadrage.md:421-428` keep runtime validation and
     forbidden services out of the static implementation phases.

   Impact: no doc correction is required now; audit and handoff should keep
   the command boundary explicit.

## Conformities

1. AWS producer publishes canonical Avro binary records to Kinesis.

   Evidence:
   - `contracts/market-candle/v1.avsc:7-23` defines the canonical candle
     fields from `event_id` to `ingested_at`.
   - `apps/binance-producer/aws.py:35-42` encodes the candle and sets the
     Kinesis `PartitionKey`.
   - `apps/binance-producer/common.py:34-35` builds the key as
     `symbol|interval`.
   - `tests/test_producer_aws.py:41-54` validates the partition key, canonical
     Avro fields and non-JSON binary payload behavior.

2. Raw AWS keeps a technical envelope and partitions by operational metadata.

   Evidence:
   - `jobs/raw-consumer/aws.py:30-38` reads Kinesis with Spark Structured
     Streaming and decodes Avro status.
   - `jobs/raw-consumer/aws.py:45-56` preserves stream, partition key,
     sequence number, payload and decode status.
   - `jobs/raw-consumer/aws.py:64-68` writes Parquet by symbol, interval,
     ingestion date and ingestion hour.

3. Bronze and Silver keep reusable transformations in `jobs/utils`.

   Evidence:
   - `jobs/bronze-ingestion/aws.py:33-39` reads Raw, decodes via shared helpers
     and writes Bronze plus rejected rows.
   - `jobs/utils/bronze.py:11-48` contains shared Avro decode and Bronze
     valid/rejected transformations.
   - `jobs/silver-transformation/aws.py:26-27` calls shared `build_silver` and
     writes Silver S3.
   - `jobs/utils/silver.py:10-18` applies quality rules and deterministic
     deduplication before selecting `SILVER_COLUMNS`.
   - `tests/test_utils_transforms.py:92-119` validates that Silver keeps the
     expected contract for Gold.

4. Gold AWS and restitution remain in S3/Glue/Athena, not PostgreSQL.

   Evidence:
   - `jobs/gold-indicators/aws.py:52-53` computes indicators and writes Gold
     Parquet.
   - `jobs/gold-indicators/aws.py:60-69` materializes the shared restitution
     tables and writes them to `trading_gold` paths.
   - `jobs/serving-datamart/registry.py:18-35` declares the four restitution
     tables.
   - `infra/aws/batch/glue_catalog.tf:260-301` declares the
     `trading_gold.*` Glue/Athena tables.

5. Terraform scope is coherent.

   Evidence:
   - `infra/aws/core/main.tf:32-112` declares Kinesis, ECR, CloudWatch, ECS
     task and ECS service for the producer path.
   - `infra/aws/core/iam.tf:22-25` scopes producer publishing to Kinesis.
   - `infra/aws/batch/main.tf:16-35` centralizes Raw, Bronze, Silver, rejected,
     checkpoint and output S3 paths.
   - `infra/aws/batch/glue_job.tf:397-584` declares Raw, Bronze, Silver and
     Gold Glue jobs with their artifacts.
   - `infra/aws/batch/glue_job.tf:42-155` and
     `infra/aws/batch/glue_job.tf:158-276` separate Raw streaming and lake
     transform IAM roles.

6. Deferred AWS services are kept out of Terraform.

   Evidence:
   - `docs/aws-service-iam-decisions.md:45-48` keeps DynamoDB, API,
     Streamlit and advanced Budgets/alarms as later scope.
   - Static scans over `infra/aws/*.tf` returned no match for:
     `aws_db`, `aws_rds`, `postgres`, `postgresql`, `aws_dynamodb`,
     `aws_lambda`, `aws_api_gateway`, `aws_apigateway` or
     `aws_budgets_budget`.

## Validation results

Commands run:

```powershell
git status --short
powershell -ExecutionPolicy Bypass -File .\platform.ps1 test
terraform fmt -check -recursive infra/aws
terraform -chdir=infra/aws/core validate
terraform -chdir=infra/aws/batch validate
rg -n "aws_db|aws_rds|postgres|postgresql" infra/aws -g "*.tf"
rg -n "aws_dynamodb|aws_lambda|aws_api_gateway|aws_apigateway|aws_budgets_budget" infra/aws -g "*.tf"
git diff --check
```

Results:

- `git status --short`: clean before audit edits.
- First `platform.ps1 test` attempt failed on Windows Docker access
  (`config.json` and Docker pipe access denied), not on test assertions.
- Same test command rerun with Docker access: passed, 23 tests OK.
- Follow-up `platform.ps1 test` after the `fastavro` cleanup: passed, 25 tests
  OK with 1 skipped Bronze Spark Avro classpath test.
- `terraform fmt -check -recursive infra/aws`: passed.
- `terraform -chdir=infra/aws/core validate`: passed.
- `terraform -chdir=infra/aws/batch validate`: passed.
- Forbidden AWS PostgreSQL/RDS scan: no match.
- Forbidden DynamoDB/Lambda/API Gateway/Budgets scan: no match.
- `git diff --check`: passed; Git reported an LF/CRLF normalization warning
  for `docs/phase-handoff.md`.

Not run:

- `terraform plan`;
- `terraform apply`;
- AWS CLI against a real account;
- ECS, Kinesis, Glue or Athena runtime checks.

## Recommendation

Proceed to the next cadrage phase only:
`Phase 5 prompt - Restitution, API and observability cadrage` in
`docs/aws-phase-prompts.md`.

Do not proceed to AWS runtime validation yet. Runtime validation belongs after
deployment credentials exist and the selected producer/lake/Gold/restitution
path can be checked on real AWS surfaces.

Before a runtime validation phase, address or explicitly accept:

- CI/CD or immutable artifact publication path;
- execution of the guarded Bronze invalid Avro test in a Spark/Glue classpath
  that includes `spark-avro`;
- Glue Schema Registry stance;
- Athena query role and API/dashboard access model if included in scope.
