# AWS Core Terraform

Minimal core stack for the AWS producer path.

## Scope

Creates only the durable producer runtime resources:

- Kinesis Data Stream for canonical market candle Avro records.
- ECR repository for the Binance producer image.
- ECS cluster, Fargate task definition and service.
- Dedicated ECS task role and task execution role.
- CloudWatch log group for producer logs.
- Outbound-only security group and subnet wiring for Fargate.

This stack deliberately does not create DynamoDB, Lambda, API Gateway,
Streamlit, Budgets, RDS or any AWS PostgreSQL target.

## Image Build

Terraform creates the ECR repository with immutable tags and scan-on-push, but
the producer image is built and pushed by CI/CD. The GitHub Actions workflow
tags the image with the commit SHA and passes that value as
`producer_image_tag`.

For local preparation only, the equivalent manual build is:

```powershell
cd <repo-root>
docker build `
  --build-arg INSTALL_AWS_DEPS=true `
  -t <ecr_repository_url>:<tag> `
  -f apps/binance-producer/Dockerfile .
aws ecr get-login-password --region <region> | docker login --username AWS --password-stdin <account>.dkr.ecr.<region>.amazonaws.com
docker push <ecr_repository_url>:<tag>
```

Keep `ecs_service_desired_count = 0` until a later runtime validation phase
starts the producer intentionally.

## CI/CD Backend

The module declares an empty S3 backend. Local static validation should use
`terraform init -backend=false`. The GitHub Actions workflow supplies backend
configuration from the `dev` GitHub Environment:

```text
TF_STATE_BUCKET
TF_STATE_LOCK_TABLE
TF_STATE_REGION
```

## Commands

```powershell
cd infra/aws/core
terraform init -backend=false
terraform fmt -recursive
terraform validate
terraform plan
```

Provide at least:

```hcl
vpc_id             = "vpc-..."
fargate_subnet_ids = ["subnet-...", "subnet-..."]
producer_image_tag = "..."
ecs_service_desired_count = 0
```

Use `assign_public_ip = true` only for the controlled low-cost POC case where
the selected subnets are public and no NAT path is available.

Only mark AWS runtime validation complete after the image is present in ECR,
the ECS service reaches steady state, CloudWatch logs are visible and Kinesis
receives records with the expected partition keys and payload fields.
