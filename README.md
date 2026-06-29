# Big Data Trading Platform

Unified, local and reproducible data platform for the pedagogical Hadoop/YARN
pipeline. The three legacy directories at the workspace root are unchanged and
remain temporary read-only references during migration.

## Architecture

```text
Binance REST
  -> Avro producer
  -> Kafka + Schema Registry
  -> Spark Structured Streaming raw consumer on YARN
  -> HDFS Raw (Kafka envelope Parquet)
  -> Spark Structured Streaming Bronze job on YARN
  -> HDFS Bronze (Parquet)
  -> Spark batch on YARN
  -> Hive Silver (clean candles)
  -> Spark batch on YARN
  -> Hive Gold lake (indicators)
  -> Spark batch on YARN
  -> PostgreSQL Serving datamart
```

Spark runs only on YARN. There is deliberately no Spark standalone master or
worker. Configuration, image versions and the Avro contract are versioned once
under `config/` and `contracts/`.

Airflow is available as an optional local submitter for Spark jobs. It can
submit Raw and Bronze streaming jobs, and Silver, Gold and Serving batch jobs to
YARN; it does not replace YARN.

## Requirements

- Docker Desktop with Docker Compose 2.24 or newer
- At least 10 GB of memory assigned to Docker
- GNU Make through WSL/Git Bash, or PowerShell using `platform.ps1`
- Internet access for the first image build and Spark package resolution

## Start the platform

```bash
make help
make platform-up
make status
make raw-up
make raw-stop
make bronze-up
make bronze-stop
```

Windows PowerShell equivalents:

```powershell
.\platform.ps1 help
.\platform.ps1 platform-up
.\platform.ps1 status
.\platform.ps1 raw-up
.\platform.ps1 raw-stop
.\platform.ps1 bronze-up
.\platform.ps1 bronze-stop
```

Once Bronze contains data:

```bash
make run-silver
make run-gold
make run-serving
make test
```

To use Airflow for Spark job submission:

```bash
make orchestration-up
```

Open Airflow at http://localhost:8080 with `airflow` / `airflow`. Trigger
`market_streaming_submit` to submit Raw then Bronze streaming jobs, or trigger
`market_batch_pipeline` to run Silver, Gold and Serving. Standalone DAGs are
also available for manual replay.

Deployment commands mirror the Compose fragments under `infra/compose/`:

Run `make help` or `.\platform.ps1 help` to print the available commands and
their purpose.

| Compose file | Command | Scope |
|---|---|---|
| `streaming.yml` | `make streaming-up` | Kafka, Schema Registry and Binance producers |
| `lake.yml` | `make lake-up` | HDFS, YARN and Spark History |
| `storage.yml` | `make storage-up` | PostgreSQL |
| `warehouse.yml` | `make warehouse-up` | PostgreSQL, Hive Metastore and HiveServer2 |
| `orchestration.yml` | `make orchestration-up` | Kafka, PostgreSQL, HDFS/YARN, Hive and Airflow |
| `ui.yml` | `make ui-up` | Kafka UI and Hue |
| Spark client | `make raw-up` / `make raw-stop` | Submit or stop the global raw Kafka consumer in YARN |
| Spark client | `make bronze-up` / `make bronze-stop` | Submit or stop the Bronze Spark streaming job in YARN |
| Spark client | `make run-silver` / `make run-gold` / `make run-serving` | Run the batch lake and datamart jobs on YARN |

Use `make platform-up` for the standard local platform: streaming, lake,
storage, warehouse and UI. Use `make all-up` when Airflow should be started as
well. `raw-up` and `bronze-up` remain separate because they submit Spark
streaming workloads to YARN through a temporary `spark-client` container. They
use `docker compose run --rm --no-deps`, so repeated submissions do not rebuild
or recreate infrastructure services. Stop streaming jobs with `raw-stop` and
`bronze-stop`, which kill the matching YARN application by Spark application
name.

Deployment groups are dependency-aware and idempotent. For example,
`make warehouse-up` includes PostgreSQL because Hive depends on storage. If
PostgreSQL is already running with the current Compose configuration, Docker
Compose keeps it as-is; if it is missing, Compose starts it before Hive. The
same rule applies to `orchestration-up` and `all-up`, which include storage,
streaming, lake and warehouse services before Airflow.

The default raw deployment uses one Spark streaming application for the complete
`market.candles.v1` topic. It writes the same Raw partitions by `symbol`,
`interval`, `ingestion_date` and `ingestion_hour` while avoiding 12 concurrent
Spark applications on a local YARN cluster.

| Service | URL |
|---|---|
| HDFS NameNode | http://localhost:9870 |
| YARN ResourceManager | http://localhost:8088 |
| Spark History Server | http://localhost:18080 |
| Schema Registry | http://localhost:8081 |
| Kafka UI | http://localhost:8085 |
| Hue | http://localhost:8888 |
| Airflow | http://localhost:8080 |

Hue is configured through `infra/config/hue/hue.ini`. The local UI exposes
connectors for HDFS/WebHDFS, YARN ResourceManager, HiveServer2 and PostgreSQL
databases `platform` and `trading_gold`.

## Configuration

`config/defaults.env` contains the canonical local defaults.
`config/versions.env` is the version matrix. For machine-specific overrides,
copy `config/local.env.example` to the ignored `config/local.env`.

Producer ingestion uses one Docker Compose service per `(symbol, interval)` flow
with a shared `big-data-platform/binance-producer` image. The initial flows are
`BTCUSDC`, `ETHUSDC` and `SOLUSDC` on `1s`, `1m`, `15m` and `1h`. Add flows by
adding explicit producer services in `infra/compose/streaming.yml`; application code must
not be edited for deployment configuration.

Raw consumption is global by default: one Spark job reads the complete Kafka
topic and partitions HDFS output by `symbol` and `interval`.

The development credentials in `defaults.env` are intentionally local-only.
Production secrets, TLS, Kerberos and high availability are outside this first
migration stage.

## Data conventions

- Kafka topic: `market.candles.v1`
- Kafka key: `symbol|interval`
- Invalid payload topic: `market.candles.v1.errors`
- Raw path: `/data/raw/binance/market_candles`
- Bronze path: `/data/bronze/market_candles`
- Bronze trigger: `30 seconds`
- Bronze watermark: `2 days`
- Silver table: `silver.market_candles`
- Gold table: `gold.market_indicators`
- Datamart targets: `trading_gold.market_indicators`,
  `trading_gold.market_indicators_latest`,
  `trading_gold.market_multitimeframe_signals`,
  `trading_gold.market_daily_summary`

Raw stores Kafka envelopes partitioned by `symbol`, `interval`, `ingestion_date`
and `ingestion_hour`. Bronze streams from Raw, decodes the Avro payload,
deduplicates by `event_id` with the configured watermark and writes business
partitions by `event_date`, `symbol` and `interval`. Raw and Bronze checkpoints
are stored in HDFS. Silver keeps clean closed candles, enforces minimal OHLCV
quality rules, keeps the latest record for each `(symbol, interval, open_time)`
key, and partitions Hive output by `event_date`, `symbol` and `interval`.
Gold lake calculates EMA 12/26, MACD, RSI 14 and Bollinger bands from Silver,
then writes the analytical table in Hive/Parquet. Silver and Gold use full
deterministic rebuilds, so rerunning either job does not append duplicates.
Serving reads Gold, applies SQL registry entries, and rebuilds the PostgreSQL
datamart tables for complete indicators, latest values, multi-timeframe signals
and daily summaries.

Airflow DAGs live under `orchestration/dags`. They call the same versioned
submit scripts as the Makefile:

- `raw_market_candles` -> `infra/scripts/submit-raw-consumer.sh`
- `bronze_market_candles` -> `infra/scripts/submit-bronze.sh`
- `market_streaming_submit` -> Raw then Bronze
- `silver_market_candles` -> `infra/scripts/submit-silver.sh`
- `gold_market_indicators` -> `infra/scripts/submit-gold.sh`
- `serving_market_datamart` -> `infra/scripts/submit-serving.sh`
- `market_batch_pipeline` -> Silver then Gold then Serving

For Raw and Bronze, Airflow logs show the `spark-submit` output and YARN
submission details. The long-running streaming application logs remain under
YARN and the Spark UI/History tooling.

Detailed Raw -> Bronze streaming rules are documented in
`docs/raw-to-bronze-streaming.md`.
Silver layer rules are documented in `docs/silver-layer.md`.
Gold lake rules are documented in `docs/gold-layer.md`.

## Migration boundary

Do not start new writes from the legacy producers after validating the new
producer services. Compare row counts, timestamp ranges and OHLC values before
extending the producer matrix. Archive legacy code only after Bronze, Silver and
Gold have all passed that comparison.
