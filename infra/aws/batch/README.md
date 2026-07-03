# AWS Batch Terraform

Minimal AWS batch stack for the portable Gold and restitution path.

## Scope

Creates the AWS lake and batch runtime surface:

- S3 lake bucket for `raw`, `bronze`, `silver`, `gold` and `trading_gold`
  datasets.
- Glue Data Catalog databases and external Parquet tables.
- Glue Streaming job for Avro Kinesis -> Raw S3.
- Glue Streaming job for Raw S3 -> Bronze S3 plus rejected records.
- Glue Spark batch job for Bronze -> Silver.
- Glue Spark job for `jobs/gold-indicators/aws.py`.
- IAM role and policies for the Glue job.
- CloudWatch log group for Glue execution logs.
- Athena workgroup and S3 query result location.

This stack deliberately does not create RDS/PostgreSQL, DynamoDB, API Gateway,
Lambda, Streamlit, alarms or Budgets resources. The later serving/API surface
lives in `infra/aws/serving`. The Kinesis stream itself lives in
`infra/aws/core`; this stack receives its name and ARN as variables.

Glue scripts, Python zips and SQL files are referenced below
`glue_artifacts_prefix/glue_artifact_version`. The default local mode uploads
them from the workspace into the lake bucket with
`glue_artifact_version = "local-dev"`.

CI/CD publishes immutable artifacts first, then applies Terraform with:

```hcl
glue_artifact_bucket_name           = "<artifact-bucket>"
glue_artifact_version               = "<commit-sha>"
upload_glue_artifacts_from_workspace = false
```

In CI mode, Terraform consumes the published S3 keys and does not zip or upload
Glue source files from the working tree.

## CI/CD Backend

The module declares an empty S3 backend. Local static validation should use
`terraform init -backend=false`. The GitHub Actions workflow supplies backend
configuration from the `dev` GitHub Environment.

## Commands

```powershell
cd infra/aws/batch
terraform init -backend=false
terraform fmt -recursive
terraform validate
terraform plan
```

The lake ingestion jobs expect the Kinesis stream from `infra/aws/core` and
produce Silver Parquet at the `silver_input_path` output. Raw and Bronze are
streaming jobs; Silver and Gold are batch jobs. Do not run those Glue jobs as
part of the CI/CD implementation phase. Only a later runtime validation phase
should start jobs and check S3 outputs, Glue tables and Athena queries in the
target AWS account.
