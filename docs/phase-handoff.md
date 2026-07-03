# Phase Handoff

Living handoff document for Codex agents. Read this file before starting a new
phase, then update it at the end of the phase.

## Current Context

The project is an on-premise Spark/YARN/HDFS/Hive/Airflow/PostgreSQL platform
that is being made portable to AWS progressively. The on-premise platform must
remain functional while AWS entry points are added phase by phase.

Current stable on-premise architecture:

```text
Binance REST -> Kafka/Schema Registry -> Raw HDFS -> Bronze HDFS
-> Silver Hive -> Gold Hive -> Serving PostgreSQL
```

Current prepared AWS architecture:

```text
Binance REST -> ECS/Fargate producer -> Kinesis Data Stream
-> Glue Streaming Raw S3 -> Glue batch Bronze S3 -> Glue batch Silver S3
-> Glue Spark Gold S3 -> trading_gold S3 -> Glue Data Catalog -> Athena
-> DynamoDB latest projection -> API Gateway/Lambda -> Cognito/Streamlit
```

PostgreSQL remains an on-premise Serving target only. RDS/PostgreSQL is not part
of the current AWS target.

No local AWS credentials are currently available for runtime validation:
`aws sts get-caller-identity` returns `Unable to locate credentials`. The
GitHub CLI is also unavailable locally: `gh` is not recognized as a command.
AWS checks must therefore be reported as static/local only unless a real AWS
account and GitHub environment are used.

## Previous Proven Baseline

On-premise Silver -> Gold -> Serving runtime proof was already obtained before
the AWS phases:

- YARN applications `silver-market-candles`, `gold-market-indicators` and
  `serving-market-datamart` finished with `SUCCEEDED`.
- Hive/HDFS `gold.market_indicators` was validated with 1476 rows.
- PostgreSQL Serving tables were filled:
  - `market_indicators`: 1476 rows;
  - `market_indicators_latest`: 12 rows;
  - `market_multitimeframe_signals`: 300 rows;
  - `market_daily_summary`: 6 rows.
- Spark History event logs/API were checked for the three applications.

AWS preparation before this phase:

- `apps/binance-producer/aws.py` exists as the Kinesis producer entry point and
  retries failed `PutRecords` entries with bounded attempts.
- `infra/aws/core` exists for Kinesis, ECR, ECS/Fargate, IAM and producer logs.
- `jobs/raw-consumer/aws.py`, `jobs/bronze-ingestion/aws.py` and
  `jobs/silver-transformation/aws.py` prepare Kinesis -> Raw/Bronze/Silver S3.
- `jobs/gold-indicators/aws.py` reads Silver Parquet from S3, writes Gold
  Parquet, then materializes `trading_gold.*` Parquet datasets.
- `infra/aws/batch` exists for S3, Glue jobs, Glue Catalog and Athena.
- `apps/aws-serving-api`, `apps/streamlit-dashboard` and `infra/aws/serving`
  prepare DynamoDB latest metrics, API Gateway/Lambda, Cognito, Streamlit
  Cloud wiring, alarms and Budget.

## Last Completed Phase

Phase: Phase 10 - AWS automated deployment and runtime validation.

Goal: harden the GitHub Actions/Terraform AWS deployment path so that, after
one-time GitHub/AWS bootstrap, a push to `main` validates, publishes immutable
artifacts, deploys the dev/POC AWS stack and runs controlled runtime
validation.

Status: completed as static/local implementation and documentation. AWS runtime
validation was not executed because AWS credentials and GitHub CLI access are
missing in the local environment.

## Changes Completed

- Hardened `.github/workflows/aws-deploy.yml`:
  - workflow-level permissions are `contents: read` only;
  - OIDC `id-token: write` is scoped to AWS deployment jobs;
  - deployment jobs use GitHub Environment `dev`;
  - AWS credential steps include allowed account guard, masked account id,
    explicit role session name and unset-current-credentials;
  - third-party actions are pinned to full commit SHAs:
    - `actions/checkout@v6.0.1` ->
      `8e8c483db84b4bee98b60c0593521ed34d9990e8`;
    - `actions/setup-python@v6.1.0` ->
      `83679a892e2d95755f2dac6acb0bfd1e9ac5d548`;
    - `aws-actions/configure-aws-credentials@v6.1.0` ->
      `ec61189d14ec14c8efccab744f656cffd0e33f37`;
    - `hashicorp/setup-terraform@v3` ->
      `b9cd54a3c349d3f38e8881555d616ced269862dd`;
  - Terraform backend config now uses S3 lockfiles with
    `use_lockfile=true`;
  - `TF_STATE_LOCK_TABLE` is no longer part of the normal GitHub Environment
    variable contract;
  - a `runtime-validation` job runs after Terraform apply on non-PR runs.
- Raised AWS Terraform stack constraints to `required_version >= 1.14.0` and
  the CI Terraform version to `1.15.7`.
- Added `infra/scripts/aws-runtime-validate.py`:
  - reads Terraform outputs for `core`, `batch` and `serving`;
  - verifies immutable ECR/S3 artifacts;
  - runs the controlled ECS/Kinesis/Glue/S3/Athena/DynamoDB/API/observability
    runtime checks when AWS is available;
  - writes `build/aws-runtime-evidence.json`;
  - always attempts to scale ECS desired count back to `0` and stop Raw Glue
    Streaming.
- Added `infra/aws/README.md` explaining:
  - one-time GitHub/AWS bootstrap;
  - OIDC trust policy for
    `repo:JulienDira/big_data_platform:environment:dev`;
  - required GitHub Environment variables;
  - S3 backend lockfile requirements;
  - push-to-main flow;
  - runtime proof checks;
  - cleanup and cost control.
- Updated focused tests:
  - workflow guardrails and SHA pinning;
  - deployment README contract;
  - runtime validation script dry-run, evidence and cleanup behavior.
- Updated deployment decision docs:
  - `docs/aws-cicd-deployment-cadrage.md`;
  - `docs/aws-service-iam-decisions.md`;
  - `infra/aws/core/README.md`.

No RDS/PostgreSQL AWS target, new AWS service family, direct Streamlit AWS SDK
access or broad data pipeline refactor was introduced.

## Validation Completed

Repository state and source control:

- `git status --short --untracked-files=all` was checked before changes. The
  tree already contained Phase 9 modified/untracked files:
  `apps/binance-producer/aws.py`, `cadrage.md`,
  `docs/aws-phase-prompts.md`, `docs/aws-service-iam-decisions.md`,
  `docs/phase-handoff.md`, `tests/test_producer_aws.py` and
  `docs/aws-implementation-step-audit.md`. They were preserved.
- Action tag SHAs were resolved with approved network access through
  `git ls-remote`.

Static/local validation:

- First `powershell -ExecutionPolicy Bypass -File .\platform.ps1 test` failed
  on Docker access:
  `C:\Users\julie\.docker\config.json: Access is denied` and Docker pipe
  access denied.
- The same command was rerun with approved Docker access. The first rerun
  exposed a Python 3.8 importlib/dataclass issue in the new test harness.
- After fixing the test import, `powershell -ExecutionPolicy Bypass -File .\platform.ps1 test`
  passed: 51 tests OK, 1 skipped because the local Spark classpath lacks the
  `spark-avro` package.
- `terraform fmt -check -recursive infra/aws` passed.
- Initial Terraform provider initialization for `core`, `batch` and `serving`
  failed because sandboxed network access to `registry.terraform.io` was
  blocked.
- After approved provider-initialization network access:
  - `terraform -chdir=infra/aws/core init -backend=false -input=false`
    succeeded with `hashicorp/aws v5.100.0`;
  - `terraform -chdir=infra/aws/batch init -backend=false -input=false`
    succeeded with `hashicorp/aws v5.100.0` and `hashicorp/archive v2.8.0`;
  - `terraform -chdir=infra/aws/serving init -backend=false -input=false`
    succeeded with `hashicorp/aws v5.100.0` and `hashicorp/archive v2.8.0`.
- `terraform -chdir=infra/aws/core validate` passed.
- `terraform -chdir=infra/aws/batch validate` passed.
- `terraform -chdir=infra/aws/serving validate` passed.
- `rg -n "aws_db|aws_rds|postgres|postgresql" infra/aws -g "*.tf"`
  returned no match.
- `rg -n "AWS_ACCESS_KEY_ID|AWS_SECRET_ACCESS_KEY|aws-access-key-id|aws-secret-access-key|secrets\." .github\workflows\aws-deploy.yml`
  returned no match.
- `rg -n "TF_STATE_LOCK_TABLE|dynamodb_table" .github\workflows\aws-deploy.yml infra/aws\README.md docs\aws-cicd-deployment-cadrage.md`
  returned no match.
- `git diff --check` passed with LF/CRLF normalization warnings on Windows.

Runtime and deployment availability checks:

- `aws sts get-caller-identity` failed with:
  `Unable to locate credentials. You can configure credentials by running "aws login".`
- `gh auth status` failed because `gh` is not installed or not on PATH.

## Proof Obtained

- The repository now contains a hardened push-to-main AWS deployment path using
  job-scoped GitHub OIDC, scoped-role inputs, account guardrails, immutable
  ECR/S3 artifacts and S3 backend lockfiles.
- The workflow includes a controlled non-PR runtime-validation job.
- The runtime validation script is implemented and unit-tested for dry-run
  evidence output and cleanup behavior.
- Local unit/static tests and Terraform validation pass.
- Static scans show no AWS RDS/PostgreSQL target, no long-lived AWS key path in
  the workflow and no legacy Terraform lock-table contract in the normal docs
  or workflow.

## Not Yet Proven

- GitHub Environment `dev` exists with required variables.
- GitHub OIDC provider and scoped deploy role exist and trust the expected
  repository/environment subject.
- Terraform state bucket and S3 lockfile permissions exist.
- The workflow runs successfully on GitHub.
- AWS producer image exists in ECR.
- Glue and Lambda artifacts exist in S3.
- Terraform apply succeeds in the target AWS account.
- ECS service steady state and controlled scale-down.
- Kinesis record ingestion in AWS.
- Glue Streaming consumption from Kinesis.
- Raw/Bronze/Silver S3 outputs in AWS.
- Glue Gold execution and `trading_gold` outputs.
- Glue Data Catalog visibility in AWS.
- Athena query execution.
- DynamoDB latest table deployment and projection execution.
- API Gateway/Lambda deployment and endpoint behavior.
- Cognito Hosted UI login, groups and JWT authorizer behavior.
- Streamlit Cloud deployment and authentication flow.
- CloudWatch alarms, SNS notifications and AWS Budget visibility.
- `build/aws-runtime-evidence.json` from a real AWS runtime-validation run.

## Next Recommended Phase

Perform the one-time GitHub/AWS bootstrap described in `infra/aws/README.md`,
then run the GitHub Actions workflow through a push to `main` or
`workflow_dispatch`.

If bootstrap is complete and the workflow succeeds, record the
`build/aws-runtime-evidence.json` contents and recommend a narrow
stabilization/demo-hardening phase.

If the workflow or runtime validation fails, recommend one targeted remediation
phase named after the failing surface, for example OIDC trust, Terraform state,
ECR artifact publication, ECS/Kinesis, Glue Raw, Glue Bronze/Silver, Glue Gold,
Athena, DynamoDB projection or API Gateway/Cognito.

Ready-to-use next-agent prompt:

```text
Mission:
Run the deployed Phase 10 GitHub Actions path in a real AWS/GitHub environment
after completing the bootstrap in infra/aws/README.md.

Before doing anything, read AGENTS.md, cadrage.md, docs/phase-handoff.md,
infra/aws/README.md and .github/workflows/aws-deploy.yml. Confirm GitHub
Environment dev has AWS_ACCOUNT_ID, AWS_DEPLOY_ROLE_ARN, AWS_REGION,
AWS_ARTIFACT_BUCKET, TF_STATE_BUCKET, TF_STATE_REGION, VPC_ID,
FARGATE_SUBNET_IDS, STREAMLIT_CALLBACK_URLS, STREAMLIT_LOGOUT_URLS and
API_CORS_ALLOWED_ORIGINS. Confirm the AWS OIDC provider, deploy role trust,
state bucket and S3 lockfile permissions exist.

Run the workflow from GitHub, not with local long-lived AWS keys. Capture exact
evidence from the GitHub run, Terraform outputs and build/aws-runtime-evidence.json.
Do not claim AWS runtime proof if any bootstrap, permission or service check is
missing.
```

## Suggested Commit Message

```text
ci: harden AWS deployment runtime validation
```
