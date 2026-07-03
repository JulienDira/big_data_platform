# AWS deployment and runtime validation

This directory contains the AWS Terraform stacks for the controlled dev/POC
deployment path.

Normal deployment path:

```text
push main -> validate -> publish immutable artifacts -> terraform apply dev
-> controlled runtime validation
```

The normal GitHub deployment credential is GitHub Actions OIDC with a scoped AWS
deploy role. Do not configure `AWS_ACCESS_KEY_ID` or `AWS_SECRET_ACCESS_KEY` as
the normal path. If an administrator credential is needed, use it only for the
one-time AWS bootstrap outside the recurring workflow.

Official references used for this setup:

- GitHub OIDC for AWS:
  https://docs.github.com/en/actions/how-tos/secure-your-work/security-harden-deployments/oidc-in-aws
- GitHub Environments:
  https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments
- Secure use of GitHub Actions:
  https://docs.github.com/en/actions/reference/security/secure-use
- `aws-actions/configure-aws-credentials`:
  https://github.com/aws-actions/configure-aws-credentials
- AWS IAM OIDC role setup:
  https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_create_for-idp_oidc.html
- AWS IAM best practices:
  https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html
- Terraform automation:
  https://developer.hashicorp.com/terraform/tutorials/automation/automate-terraform
- Terraform S3 backend and lockfiles:
  https://developer.hashicorp.com/terraform/language/backend/s3
- Amazon ECR image tag immutability:
  https://docs.aws.amazon.com/AmazonECR/latest/userguide/image-tag-mutability.html
- EventBridge Scheduler schedule types:
  https://docs.aws.amazon.com/scheduler/latest/UserGuide/schedule-types.html
- Step Functions optimized Glue integration:
  https://docs.aws.amazon.com/step-functions/latest/dg/connect-glue.html
- Step Functions DynamoDB integration:
  https://docs.aws.amazon.com/step-functions/latest/dg/connect-ddb.html

## One-time bootstrap

Bootstrap is manual because it creates the trust anchor used by the CI/CD path.
Use a human-controlled admin session only for this step.

1. Create or verify the Terraform state S3 bucket:
   - server-side encryption enabled;
   - versioning enabled;
   - public access blocked;
   - lifecycle rules appropriate for a POC;
   - permissions for Terraform state objects under
     `big-data-platform/dev/*.tfstate`;
   - permissions for S3 lockfiles under the matching `.tflock` keys.
2. Create or verify the artifact S3 bucket used by GitHub Actions:
   - encrypted;
   - public access blocked;
   - write access limited to immutable prefixes such as
     `artifacts/glue/<commit-sha>/` and `artifacts/lambda/<commit-sha>/`.
3. Create the GitHub OIDC identity provider if the AWS account does not already
   have it:
   - provider URL: `https://token.actions.githubusercontent.com`;
   - audience: `sts.amazonaws.com`.
4. Create the scoped AWS deploy role trusted by GitHub Actions.
5. Configure GitHub Environment `dev` with the required variables below.

Trust policy conditions for this repository should include:

```json
{
  "StringEquals": {
    "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
    "token.actions.githubusercontent.com:sub": "repo:JulienDira/big_data_platform:environment:dev"
  }
}
```

Policy note to verify around July 15, 2026: if this repository opts into
GitHub immutable OIDC subject claims, confirm the deploy role trust policy still
matches the subject claim shape before running the workflow.

## GitHub Environment variables

Required variables in GitHub Environment `dev`:

| Variable | Purpose |
|---|---|
| `AWS_ACCOUNT_ID` | Allowed AWS account guard for OIDC sessions. |
| `AWS_DEPLOY_ROLE_ARN` | Scoped deploy role assumed through OIDC. |
| `AWS_REGION` | Region for AWS resources, for example `eu-west-3`. |
| `AWS_ARTIFACT_BUCKET` | S3 bucket for Glue and Lambda artifacts. |
| `TF_STATE_BUCKET` | S3 bucket for Terraform remote state and lockfiles. |
| `TF_STATE_REGION` | Region of the Terraform state bucket. |
| `VPC_ID` | VPC used by the ECS/Fargate producer service. |
| `FARGATE_SUBNET_IDS` | Terraform list expression, for example `["subnet-a","subnet-b"]`. |
| `STREAMLIT_CALLBACK_URLS` | Terraform list expression for Cognito callbacks. |
| `STREAMLIT_LOGOUT_URLS` | Terraform list expression for Cognito logout URLs. |
| `API_CORS_ALLOWED_ORIGINS` | Terraform list expression for API CORS origins. |

Optional variables:

| Variable | Purpose |
|---|---|
| `ALERT_EMAIL` | Enables SNS email notifications and Budget thresholds. |
| `RUNTIME_PRODUCER_SECONDS` | Overrides the bounded producer runtime window. |

No GitHub secret is required for AWS access in the normal path. The deploy role
must grant only the actions needed by Terraform, artifact publication and
runtime validation for this POC. Scope permissions to the project/environment
resource names where practical, and restrict `iam:PassRole` to the Terraform
managed ECS, Glue and Lambda roles.

## Push-to-main flow

Pull requests run validation only:

- unit/static tests;
- Terraform format check;
- Terraform validation with `-backend=false`;
- guardrail scans for forbidden AWS RDS/PostgreSQL and long-lived key usage.

Pushes to `main` and manual `workflow_dispatch` run:

1. `validate`
2. `publish-artifacts`
   - assumes the deploy role through OIDC;
   - applies `infra/aws/core` with `ecs_service_desired_count = 0`;
   - builds the producer image;
   - pushes the ECR image with tag `${github.sha}`;
   - packages Glue scripts, Python zips, SQL, Avro contract and Lambda zip;
   - uploads S3 artifacts under commit-SHA prefixes.
3. `terraform-apply`
   - uses Terraform S3 backend lockfiles with `use_lockfile=true`;
   - applies `infra/aws/batch`;
   - applies `infra/aws/serving`;
   - applies `infra/aws/orchestration`;
   - keeps the direct projection schedule and batch pipeline schedule disabled
     by default.
4. `runtime-validation`
   - runs `infra/scripts/aws-runtime-validate.py`;
   - writes `build/aws-runtime-evidence.json`.

## Scheduled batch orchestration

`infra/aws/orchestration` prepares the regular batch chain after Raw:

```text
EventBridge Scheduler rate(1 minute)
-> Step Functions
-> Glue Bronze batch
-> Glue Silver batch
-> Glue Gold/trading_gold batch
-> latest projection Lambda
-> DynamoDB latest metrics
```

The Step Functions workflow uses a DynamoDB conditional lock so a one-minute
trigger does not overlap a previous batch run. The schedule is deployed with
`batch_pipeline_schedule_enabled=false` by default. Enable it only after the
AWS bootstrap, deployment and controlled runtime validation prove the pipeline
can run safely.

## Runtime proof checks

The runtime validation script checks:

- ECR contains the producer image tagged with the commit SHA.
- S3 contains the immutable Glue and Lambda artifacts.
- Raw Glue Streaming can start.
- ECS producer can scale to one task, reach stability, publish briefly, then
  scale back to zero.
- Raw, Bronze, Silver, Gold and `trading_gold` S3 prefixes contain objects.
- Bronze, Silver and Gold Glue jobs finish with `SUCCEEDED`.
- Step Functions runs Bronze, Silver, Gold and latest projection in order.
- EventBridge Scheduler can trigger the state machine when explicitly enabled.
- Athena count queries on `trading_gold.market_indicators` and
  `trading_gold.market_indicators_latest` return rows.
- Latest projection Lambda writes DynamoDB items.
- API Lambda health responds through direct Lambda invocation.
- API Gateway rejects an unauthenticated request, proving the JWT authorizer is
  active.
- CloudWatch alarms and the POC Budget exist.

Do not mark AWS runtime validation complete unless these checks run against a
real AWS account and the evidence file records success.

## Cleanup and cost control

The workflow leaves durable dev/POC infrastructure deployed, but the validation
script always attempts to stop cost-bearing runtime activity:

- set ECS producer desired count back to `0`;
- stop the Raw Glue Streaming job run.

For manual cleanup, destroy in reverse dependency order only after confirming
that no runtime validation is in progress:

```powershell
terraform -chdir=infra/aws/orchestration destroy
terraform -chdir=infra/aws/serving destroy
terraform -chdir=infra/aws/batch destroy
terraform -chdir=infra/aws/core destroy
```

Cost controls:

- keep the ECS desired count at `0` outside the bounded validation window;
- keep Glue worker count low for POC validation;
- keep `batch_pipeline_schedule_enabled=false` unless a later controlled AWS
  runtime phase explicitly enables the one-minute batch chain;
- keep `projection_schedule_enabled=false` unless a later phase explicitly
  enables it;
- configure `ALERT_EMAIL` so the 50 EUR AWS Budget can notify at configured
  thresholds;
- inspect CloudWatch logs, Glue runs, Athena query results and the evidence
  file before rerunning a failed deployment.

## Missing bootstrap behavior

If the OIDC role, Terraform state bucket, lockfile permissions, GitHub
Environment variables, AWS credentials or GitHub permissions are missing, the
workflow cannot produce AWS runtime proof. Record the exact failing command or
GitHub job message in `docs/phase-handoff.md` and keep the phase status as
prepared or blocked, not runtime validated.
