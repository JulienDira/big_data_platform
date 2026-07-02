# AGENTS.md

Guidelines for Codex and other coding agents working in this repository.

## Mission

Keep the on-premise platform working while making the business logic portable to
AWS step by step. Prefer small, readable changes over broad rewrites.

Current on-premise chain:

```text
Binance REST -> Kafka/Schema Registry -> Raw HDFS -> Bronze HDFS
-> Silver Hive -> Gold Hive -> Serving PostgreSQL
```

Target AWS direction:

```text
Binance -> Kinesis -> Glue/Spark -> S3 medallion layers
-> Glue Data Catalog/Athena -> DynamoDB latest metrics when needed
-> API Gateway/Lambda/Streamlit later
```

PostgreSQL is an on-premise Serving target only. Do not introduce RDS as an AWS
target for this project unless the product scope is explicitly changed.

## Repository Structure Rules

Use a job-oriented structure:

```text
jobs/<pipeline-step>/main.py   # current on-prem/local entry point
jobs/<pipeline-step>/aws.py    # AWS entry point, only when needed
jobs/utils/                    # shared transformations and helpers
```

Examples:

```text
jobs/gold-indicators/main.py   # Hive/YARN path
jobs/gold-indicators/aws.py    # S3/Glue/Athena path
jobs/serving-datamart/main.py  # PostgreSQL on-prem Serving only
```

Do not create parallel top-level AWS job folders when the work belongs to an
existing logical pipeline step.

## Architecture Boundaries

- Keep transformations pure: DataFrame in, DataFrame out.
- Keep functions atomic: one function should express one clear business or
  technical operation.
- Do not create SparkSession objects inside shared transformation functions.
- Do not put HDFS, Hive, S3, Glue, YARN, PostgreSQL, DynamoDB or Kafka details
  inside business transformations.
- Keep reads, writes, Spark sessions and runtime arguments in entry points or
  small IO helpers.
- Use `jobs/utils` as the shared logic layer before creating any new package.
- Avoid internal frameworks, generic abstractions and dependency cycles.
- Add abstractions only when they remove real duplication or clarify execution.
- Simplicity comes first: prefer the most direct readable implementation that
  preserves the architecture boundaries.

Layer responsibilities:

- Raw preserves the source envelope and technical ingestion metadata.
- Bronze decodes payloads and applies first technical validity checks.
- Silver keeps clean, typed, deduplicated closed candles.
- Gold computes analytical indicators such as EMA, MACD, RSI and Bollinger.
- Serving PostgreSQL is an on-premise projection for consumption.
- AWS restitution tables are `trading_gold.*` datasets on S3, exposed by Glue
  Data Catalog and Athena.

## Source of Truth and Dependencies

- Maintain one source of truth for schemas, paths, table names, partitions,
  timeframes, symbols, quality rules and runtime parameters.
- Do not duplicate the same convention across entry points, SQL files and
  scripts without a clear reason.
- Keep dependencies one-directional: entry points depend on shared utilities,
  shared utilities do not depend on entry points.
- Keep environment-specific code at the edge of the system.
- Avoid circular imports and cross-layer shortcuts.
- If a value is used by multiple jobs, move it to `config/`, `contracts/` or a
  small shared helper instead of copying it.
- If two implementations start to diverge, extract the common business rule
  before adding a new environment-specific branch.

## Gold and Serving Rules

- `gold.market_indicators` is the analytical Gold output.
- Technical indicators stay in Gold, not in Serving.
- Restitution transformations such as latest indicators, multitimeframe signals
  and daily summaries must be reusable by on-premise and AWS.
- On-premise Serving writes those restitution outputs to PostgreSQL.
- AWS writes those restitution outputs as Parquet datasets under
  `trading_gold.*`; Athena reads cataloged tables and is not an output writer.
- DynamoDB is only a later cache or latest-metrics store, not the historical
  analytical source of truth.

## Coding Style

- Keep entry points thin and explicit:
  `read_source -> apply_schema -> apply_quality_rules -> transform -> write`.
- Use clear, domain-specific function names.
- Prefer plain functions over classes unless state or an interface is truly
  needed.
- Keep modules small and local to the layer they support.
- Favor readable orchestration over clever generic code.
- Avoid over-engineering: do not add factories, base classes, plugins or
  framework-like layers unless the repo has a repeated concrete need.
- Do not hardcode symbols, intervals, table names, paths or JDBC/S3 details in
  transformations; use config/env/contract helpers.
- Use structured Spark APIs rather than ad hoc string manipulation where
  practical.
- Keep comments short and useful; do not narrate obvious assignments.
- Use ASCII in new files unless an existing file already uses another encoding.

## Configuration and Contracts

- `contracts/market-candle/v1.avsc` is the canonical event contract.
- `config/defaults.env` holds local defaults and table/path names.
- Timeframes, symbols, paths, partitions, table names and quality rules should
  have one source of truth.
- If a new table is added to Serving, register it through the SQL registry and
  SQL files, not by hardcoding one-off logic in `main.py`.

## DevOps and Execution

- Keep Docker Compose/YARN/HDFS/Hive/PostgreSQL working.
- Airflow submits jobs; it is not the streaming runtime truth.
- YARN/Spark History/HDFS/Hive/PostgreSQL are the runtime proof surfaces.
- Use `platform.ps1` on Windows when `make` is unavailable.
- Do not treat missing AWS credentials as a blocker for implementation work.
- When the AWS account is not available, develop code and Terraform with
  static/local validation first, then reserve runtime proof for the moment
  credentials and an AWS account are available.
- Do not collapse all AWS target services into the same next phase.
- Cadrer first how the existing producer, Spark jobs, shared logic, Terraform
  and CI/CD should be reused on AWS.
- Implement the core AWS portability path after that cadrage: producer
  packaging, ECR/ECS or chosen alternative, Kinesis integration, Glue/Spark
  packaging and S3/Glue/Athena wiring.
- After the producer/Kinesis/ECS core is prepared, do not jump directly to AWS
  runtime validation. First cadrer and implement the missing Kinesis -> S3
  Raw/Bronze/Silver ingestion and lake path, then reserve AWS runtime proof for
  the complete developed path.
- Cadrer DynamoDB latest metrics, API Gateway/Lambda, Streamlit/local
  dashboard support, CloudWatch alarms and AWS Budgets in a later phase before
  implementing them.
- After the static AWS quality audit, cadrer and implement a simple automated
  CI/CD and deployment preparation path before recommending global AWS runtime
  validation.
- The target AWS deployment path should use GitHub Actions with AWS OIDC,
  immutable ECR/S3 artifacts and Terraform inputs. Do not rely on long-lived
  AWS access keys in GitHub as the normal path.

## Validation Rules

Use the repo validation path:

```powershell
.\platform.ps1 test
```

If PowerShell execution policy blocks it, run with process-level bypass:

```powershell
powershell -ExecutionPolicy Bypass -File .\platform.ps1 test
```

When compiling Python in the Docker Spark client, redirect pycache to `/tmp` if
the workspace is mounted read-only:

```text
PYTHONPYCACHEPREFIX=/tmp/pycache python3 -m py_compile ...
```

Always distinguish:

- unit/static validation;
- Spark local validation;
- static quality/conformance audit against repo rules and provider guidance;
- true runtime validation on YARN/HDFS/Hive/PostgreSQL;
- AWS runtime validation on Kinesis/ECS/S3 Raw-Bronze-Silver/Glue/Athena.
- AWS CI/CD/deployment preparation, which may publish immutable artifacts and
  apply dev/POC Terraform but still does not prove service runtime behavior.

Do not claim end-to-end validation unless the actual runtime surfaces were
checked.

If AWS credentials or permissions are unavailable, record AWS checks as
prepared or statically validated only. Do not make the next phase only a
runtime-validation phase when the AWS target services still need to be built.
After a broad AWS implementation phase, run a static quality/conformance audit
and then the CI/CD/deployment preparation phase before global AWS runtime
validation unless the user explicitly changes that order.

## Documentation Rules

- Update `cadrage.md` when an architecture rule changes.
- Update `jobs/README.md` when job layout or entry points change.
- Update layer docs such as `docs/gold-layer.md` when Gold/Serving semantics
  change.
- Update `docs/phase-handoff.md` at the end of every completed phase.
- Keep wording simple, direct and consistent with the repo reality.
- Explicitly mark what is implemented, what is prepared and what still needs
  runtime proof.

## Phase Workflow

Every new phase must start from repository truth, not from conversation history
alone.

Before changing files:

1. Read `AGENTS.md`.
2. Read `cadrage.md`.
3. Read `docs/phase-handoff.md`.
4. Inspect the actual repo with `rg`, direct file reads and relevant tests.
5. Confirm what is implemented, prepared, validated and still unproven.

At the end of a phase:

1. Update `docs/phase-handoff.md` with completed work, changed files,
   validation results, missing proof and the next recommended phase.
2. Update `cadrage.md` if architecture or migration scope changed.
3. Update `AGENTS.md` if a stable coding or agent rule changed.
4. Update local docs such as `jobs/README.md` or layer docs when their area
   changed.
5. Provide one simple, synthetic commit message proposal that follows good
   commit practices: imperative summary, clear scope, no vague wording and no
   long multi-topic paragraph.

Use `docs/phase-template.md` when planning or closing a phase. Keep the handoff
short enough to be read before implementation, but explicit enough for a new
agent to resume without hidden context.

## Preferred Change Strategy

- Read the current code and docs before proposing structural changes.
- Preserve existing working paths unless the change is necessary.
- Make the smallest coherent change that advances portability.
- Avoid broad refactors during feature work.
- Keep on-premise behavior stable while adding AWS entry points.
- Prefer a short implementation note plus validation result when finishing.
