# AWS CI/CD and automated deployment cadrage

## Objective

Frame the minimal AWS CI/CD and deployment system required before any global
AWS runtime validation.

The target is simple:

```text
push to main -> validate -> publish immutable artifacts -> terraform apply dev
```

After the one-time AWS/GitHub bootstrap, no local deployment command should be
needed for normal fixes. A push to `main` must publish the producer image, Glue
artifacts and Lambda package, then apply the prepared Terraform stacks for the
controlled dev/POC environment.

This cadrage does not implement the workflow and does not run AWS runtime
validation.

Implementation status on 2026-07-02:

- `.github/workflows/aws-deploy.yml` implements the target GitHub Actions path;
- `infra/scripts/package-aws-artifacts.py` packages Glue and Lambda artifacts;
- Terraform modules now declare S3 backend blocks for CI and keep
  `terraform init -backend=false` as the local static validation path;
- runtime remains disabled by default: ECS desired count is `0`, Glue jobs are
  not started by the workflow, and the projection schedule stays disabled.

## References and standards used

- GitHub recommends AWS OIDC for GitHub Actions so workflows do not need
  long-lived AWS access keys in repository secrets:
  <https://docs.github.com/en/actions/how-tos/secure-your-work/security-harden-deployments/oidc-in-aws>
- GitHub Environments can hold environment variables/secrets and deployment
  protection rules:
  <https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments>
- HashiCorp recommends non-interactive Terraform automation with explicit
  inputs and remote state/locking for repeatable automated runs:
  <https://developer.hashicorp.com/terraform/tutorials/automation/automate-terraform>
- AWS documents ECR image tag immutability and image scanning for repeatable
  image publication:
  <https://docs.aws.amazon.com/AmazonECR/latest/userguide/image-tag-mutability.html>
  and <https://docs.aws.amazon.com/AmazonECR/latest/userguide/image-scanning.html>
- Lambda supports both zip archives and container images, but the package type
  cannot be changed for an existing function:
  <https://docs.aws.amazon.com/lambda/latest/dg/python-package.html>
  and <https://docs.aws.amazon.com/lambda/latest/dg/images-create.html>

## Target CI/CD shape

Use GitHub Actions on `ubuntu-latest`.

Target workflow:

```text
.github/workflows/aws-deploy.yml
```

Triggers:

- `pull_request`: validate only, no artifact publication, no apply.
- `push` on `main`: validate, publish artifacts, run Terraform plan/apply for
  dev/POC.
- optional `workflow_dispatch`: manual rerun for the same dev/POC path.

Authentication:

- use GitHub OIDC with `id-token: write`;
- assume `AWS_DEPLOY_ROLE_ARN` with `aws-actions/configure-aws-credentials`;
- do not store `AWS_ACCESS_KEY_ID` or `AWS_SECRET_ACCESS_KEY` in GitHub unless
  there is a documented emergency fallback;
- restrict the AWS trust policy to this repository, the `main` branch and the
  selected GitHub environment.

Artifact version:

```text
ARTIFACT_VERSION=${github.sha}
```

Every image, Glue artifact and Lambda package published by the workflow must
use that immutable version. Do not use mutable deployment tags such as `latest`
for Terraform inputs.

## One-time bootstrap

The project needs one explicit bootstrap before push-based deployment can work:

1. Create or apply an AWS bootstrap stack for:
   - Terraform state S3 bucket;
   - Terraform state lock table or equivalent locking mechanism;
   - GitHub OIDC IAM provider if it is not already present;
   - GitHub deploy IAM role scoped to this repository/environment;
   - artifact bucket used by CI for Glue and Lambda packages.
2. Configure GitHub Environment `dev` with variables:
   - `AWS_REGION`;
   - `AWS_DEPLOY_ROLE_ARN`;
   - `AWS_ARTIFACT_BUCKET`;
   - `TF_STATE_BUCKET`, `TF_STATE_LOCK_TABLE` and `TF_STATE_REGION`;
   - `VPC_ID`;
   - `FARGATE_SUBNET_IDS` as a Terraform list expression, for example
     `["subnet-a","subnet-b"]`;
   - `STREAMLIT_CALLBACK_URLS`, `STREAMLIT_LOGOUT_URLS` and
     `API_CORS_ALLOWED_ORIGINS` as Terraform list expressions;
   - optional `ALERT_EMAIL`.
3. Keep secrets minimal. Prefer variables for non-sensitive names and OIDC for
   AWS access.

After bootstrap, normal deployment should happen through GitHub Actions only.

## Pipeline order

Recommended jobs:

1. `validate`
   - checkout;
   - run unit/static validation appropriate for the repo;
   - run `terraform fmt -check -recursive infra/aws`;
   - run Terraform validation for changed AWS stacks;
   - run forbidden-service scans for RDS/PostgreSQL AWS and direct dashboard AWS
     SDK access.
2. `publish-artifacts`
   - authenticate to AWS through OIDC;
   - apply `infra/aws/core` first with `ecs_service_desired_count=0` so the
     Kinesis stream, ECR repository and stopped ECS service exist;
   - build producer Docker image with `INSTALL_AWS_DEPS=true`;
   - push the image to ECR with tag `${github.sha}`;
   - package Glue scripts, `jobs-utils.zip`, `serving-registry.zip`, SQL and
     `contracts/market-candle/v1.avsc`;
   - upload Glue artifacts under
     `artifacts/glue/${github.sha}/...`;
   - package `apps/aws-serving-api` as a Lambda zip and upload it under
     `artifacts/lambda/${github.sha}/aws-serving-api.zip`;
   - expose artifact keys and hashes as job outputs.
3. `terraform-apply`
   - initialize Terraform with backend config and `-input=false`;
   - apply `infra/aws/batch`, passing `glue_artifact_version=${github.sha}` and
     consuming CI-published Glue artifact keys;
   - apply `infra/aws/serving`, passing the Lambda S3 package key/hash and
     keeping `projection_schedule_enabled=false` before runtime;
   - print Terraform outputs needed by the later runtime phase.

The CI pipeline may run `terraform apply` for dev/POC only after bootstrap is
complete. This is still deployment preparation, not global AWS runtime proof.

## Terraform and CI/CD boundary

Terraform owns durable resources:

- Kinesis, ECR repositories, ECS cluster/task/service and IAM;
- S3 buckets, Glue jobs, Glue Catalog, Athena workgroup and IAM;
- DynamoDB, Lambda functions, API Gateway, Cognito, alarms and Budget;
- CloudWatch log groups and permissions.

CI/CD owns built artifacts:

- producer Docker image in ECR;
- Glue scripts and dependency zips in S3;
- Avro contract file in S3;
- Lambda zip package in S3;
- immutable version values passed to Terraform.

Terraform should reference artifact versions or explicit S3 keys. In CI mode,
Terraform should not build zips from the local working tree and should not
upload source files from `path.module` as deployment artifacts.

## Producer image

Use ECR for the producer because ECS/Fargate runs containers.

Target behavior:

- repository encryption enabled;
- image scanning enabled;
- image tag immutability enabled;
- tag based on `${github.sha}`;
- no `latest` tag as a Terraform deployment input;
- ECS service desired count stays `0` until the runtime validation phase starts
  the producer intentionally.

## Glue artifacts

Glue should continue to run Python scripts from S3 with `--extra-py-files` and
`--extra-files`.

CI must publish at least:

```text
artifacts/glue/${github.sha}/jobs/raw-consumer/aws.py
artifacts/glue/${github.sha}/jobs/bronze-ingestion/aws.py
artifacts/glue/${github.sha}/jobs/silver-transformation/aws.py
artifacts/glue/${github.sha}/jobs/gold-indicators/aws.py
artifacts/glue/${github.sha}/python/jobs-utils.zip
artifacts/glue/${github.sha}/python/serving-registry.zip
artifacts/glue/${github.sha}/contracts/market-candle-v1.avsc
artifacts/glue/${github.sha}/sql/*.sql
```

`glue_artifact_version` remains the main Terraform version input.

## Lambda package decision

Default: use Zip/S3 for `apps/aws-serving-api`.

Rationale:

- the current Lambda code is lightweight Python for API reads and projection;
- zip packages are simpler for small Python functions;
- a single versioned zip in S3 is enough for reproducible deployment;
- Lambda container images require ECR repository policy and image lifecycle
  management and cannot be switched in-place from an existing zip function.

Use Lambda container images later only if one of these becomes true:

- dependencies become too large or native enough to make zip packaging fragile;
- a custom runtime is required;
- the team accepts creating or migrating functions to image package type
  explicitly.

Terraform for serving should therefore move from local `archive_file` packaging
to CI-published S3 package inputs:

```text
lambda_package_s3_bucket
lambda_package_s3_key
lambda_package_source_hash
```

## Explicit non-goals

This phase and the next CI/CD implementation phase must not:

- launch Glue jobs;
- scale ECS producer above zero as a runtime proof;
- run Kinesis ingestion checks;
- deploy Streamlit Cloud;
- run global cloud validation;
- introduce RDS/PostgreSQL on AWS;
- store long-lived AWS access keys in GitHub as the normal path.

## Next implementation prompt

```text
Mission:
Implement the simplified AWS CI/CD and deployment preparation path defined in
docs/aws-cicd-deployment-cadrage.md.

Before changes, read AGENTS.md, cadrage.md, docs/phase-handoff.md,
docs/phase-template.md, docs/aws-service-iam-decisions.md,
docs/aws-phase-prompts.md, docs/aws-static-quality-audit.md and
docs/aws-cicd-deployment-cadrage.md. Then inspect git status, .github,
infra/aws/core, infra/aws/batch, infra/aws/serving, apps/binance-producer,
apps/aws-serving-api, jobs and tests.

In scope:
- add GitHub Actions workflow on push to main and pull_request validation;
- use AWS OIDC with AWS_DEPLOY_ROLE_ARN, not long-lived AWS keys;
- add or document the bootstrap path for Terraform remote state, locking and
  the GitHub deploy role;
- publish producer Docker image to ECR with immutable commit SHA tag;
- publish Glue scripts, jobs-utils.zip, serving-registry.zip, SQL and Avro
  contract under a commit-SHA artifact version;
- publish the Lambda API/projection zip to S3 and pass its key/hash to
  Terraform;
- adjust Terraform inputs so CI consumes immutable artifact references;
- keep runtime disabled by default: ECS desired count 0, no Glue job starts,
  projection schedule disabled unless explicitly enabled later;
- update docs/phase-handoff.md with exact validation and missing runtime proof.

Out of scope:
- global AWS runtime validation;
- starting ECS/Kinesis runtime;
- running Glue jobs;
- Streamlit Cloud deployment;
- adding RDS/PostgreSQL AWS;
- using Lambda ECR images by default.

Validation:
- run repo static/unit tests if available in the environment;
- run terraform fmt/validate for changed AWS modules;
- run rg scans for forbidden AWS PostgreSQL/RDS and forbidden runtime commands;
- run git diff --check;
- do not run terraform apply unless the phase explicitly has bootstrap and
  deploy permissions and is implementing the dev/POC automation path.
```

## Proof boundary

This cadrage proves only the intended deployment shape. It does not prove:

- GitHub OIDC is configured in AWS;
- any ECR image exists;
- any artifact is uploaded to S3;
- Terraform can apply in AWS;
- ECS, Kinesis, Glue, Athena, DynamoDB, API Gateway, Lambda, Cognito,
  Streamlit Cloud, CloudWatch alarms or Budgets work at runtime.
