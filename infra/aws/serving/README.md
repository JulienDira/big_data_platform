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

## Static Commands

```powershell
cd infra/aws/serving
terraform init -backend=false
terraform fmt -recursive
terraform validate
```

Do not treat these commands as AWS runtime proof. Runtime validation requires a
separate phase with real AWS credentials, deployment and service checks.
