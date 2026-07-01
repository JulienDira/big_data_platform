# AWS Batch Terraform

Minimal AWS batch stack for the portable Gold and restitution path.

## Scope

Creates the AWS lake and batch runtime surface:

- S3 lake bucket for `raw`, `bronze`, `silver`, `gold` and `trading_gold`
  datasets.
- Glue Data Catalog databases and external Parquet tables.
- Glue Streaming job for Avro Kinesis -> Raw S3.
- Glue Spark batch jobs for Raw -> Bronze and Bronze -> Silver.
- Glue Spark job for `jobs/gold-indicators/aws.py`.
- IAM role and policies for the Glue job.
- CloudWatch log group for Glue execution logs.
- Athena workgroup and S3 query result location.

This stack deliberately does not create RDS/PostgreSQL, DynamoDB, API Gateway,
Lambda, Streamlit, alarms or Budgets resources. The Kinesis stream itself lives
in `infra/aws/core`; this stack receives its name and ARN as variables.

Glue scripts, Python zips and SQL files are uploaded below
`glue_artifacts_prefix/glue_artifact_version`. The default
`glue_artifact_version = "local-dev"` keeps local static validation simple.
CI/CD should later publish immutable artifact versions and pass that same value
to Terraform.

## Commands

```powershell
cd infra/aws/batch
terraform init
terraform fmt -recursive
terraform validate
terraform plan
```

The lake ingestion jobs expect the Kinesis stream from `infra/aws/core` and
produce Silver Parquet at the `silver_input_path` output. After `terraform
apply`, run the jobs in order and validate:

```powershell
aws glue start-job-run --job-name <raw_streaming_job_name>
aws glue start-job-run --job-name <bronze_batch_job_name>
aws glue start-job-run --job-name <silver_batch_job_name>
aws glue start-job-run --job-name <glue_job_name>
aws s3 ls <raw_output_path> --recursive
aws s3 ls <bronze_output_path> --recursive
aws s3 ls <silver_input_path> --recursive
aws s3 ls <gold_output_path> --recursive
aws s3 ls <trading_gold_output_base_path> --recursive
aws glue get-table --database-name trading_gold --name market_indicators
aws athena start-query-execution --work-group <athena_workgroup_name> --query-string "SELECT count(*) FROM trading_gold.market_indicators"
```

Only mark AWS runtime validation complete after S3 outputs, Glue tables and an
Athena query have been checked in the target AWS account.
