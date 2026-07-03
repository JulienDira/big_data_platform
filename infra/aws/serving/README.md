# AWS Serving Terraform

Static Terraform module for the POC serving, API, authentication and
observability surface.

## Scope

Creates:

- DynamoDB latest metrics cache keyed by `symbol` and `interval`.
- API Lambda and projection Lambda from `apps/aws-serving-api`.
- API Gateway HTTP API with Cognito JWT authorizer.
- Cognito User Pool, Hosted UI domain, public Streamlit app client and
  `viewer` / `admin` groups.
- CloudWatch log groups, minimal alarms, optional SNS email subscription and a
  50 EUR monthly AWS Budget.

This module does not create RDS or any AWS PostgreSQL target. Streamlit Cloud is
configured outside Terraform with the API and Cognito outputs.

## Inputs From Existing Stacks

Use outputs from `infra/aws/batch` and, if names were overridden, from
`infra/aws/core`:

```hcl
lake_bucket_name          = "<batch lake_bucket_name>"
athena_results_bucket_name = "<batch athena_results_bucket_name>"
athena_workgroup_name     = "<batch athena_workgroup_name>"
athena_output_location    = "<batch athena_output_location>"
```

Set Streamlit callback/logout URLs to the local or Streamlit Cloud URL before
runtime deployment.

## Lambda Package

Local static validation can keep the default `archive_file` packaging from
`apps/aws-serving-api`.

CI/CD publishes a versioned Zip/S3 package and applies Terraform with:

```hcl
lambda_package_s3_bucket   = "<artifact-bucket>"
lambda_package_s3_key      = "artifacts/lambda/<commit-sha>/aws-serving-api.zip"
lambda_package_source_hash = "<base64-sha256>"
```

Both the read API Lambda and the latest projection Lambda consume the same
package. Keep `projection_schedule_enabled = false` until a later runtime
validation phase intentionally enables refreshes.

## CI/CD Backend

The module declares an empty S3 backend. Local static validation should use
`terraform init -backend=false`. The GitHub Actions workflow supplies backend
configuration from the `dev` GitHub Environment.

## Static Commands

```powershell
cd infra/aws/serving
terraform init -backend=false
terraform fmt -recursive
terraform validate
```

Do not treat these commands as AWS runtime proof. Runtime validation requires a
separate phase with real AWS credentials, deployment and service checks.
