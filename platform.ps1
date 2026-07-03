param(
    [Parameter(Mandatory = $false)]
    [ValidateSet(
        "help",
        "streaming-up", "lake-up", "storage-up", "warehouse-up", "ui-up", "platform-up", "all-up",
        "orchestration-up", "raw-up", "raw-stop", "bronze-up", "bronze-stop", "status", "down",
        "run-silver", "run-gold", "run-serving", "test", "config"
    )]
    [string]$Action = "help"
)

$helpText = @"
Big Data Platform commands

.\platform.ps1 streaming-up       Start Kafka, Schema Registry and Binance producers.
.\platform.ps1 lake-up            Start HDFS, YARN and Spark History.
.\platform.ps1 storage-up         Start PostgreSQL.
.\platform.ps1 warehouse-up       Start storage plus Hive Metastore and HiveServer2.
.\platform.ps1 orchestration-up   Start streaming, lake, warehouse and Airflow.
.\platform.ps1 ui-up              Start Kafka UI and Hue.
.\platform.ps1 platform-up        Start the standard local platform without Airflow.
.\platform.ps1 all-up             Start the standard platform plus Airflow.
.\platform.ps1 raw-up             Submit the Raw Spark streaming consumer to YARN.
.\platform.ps1 raw-stop           Stop the Raw Spark streaming consumer in YARN.
.\platform.ps1 bronze-up          Submit the Bronze Spark streaming job to YARN.
.\platform.ps1 bronze-stop        Stop the Bronze Spark streaming job in YARN.
.\platform.ps1 status             Show Compose service status.
.\platform.ps1 down               Stop and remove Compose containers.
.\platform.ps1 run-silver         Run the Silver batch job.
.\platform.ps1 run-gold           Run the Gold batch job.
.\platform.ps1 run-serving        Run the PostgreSQL Serving datamart job.
.\platform.ps1 test               Run the platform unit tests.
.\platform.ps1 config             Render the resolved Docker Compose config.
.\platform.ps1 help               Show this help.
"@

if ($Action -eq "help") {
    Write-Output $helpText
    exit 0
}

$compose = @(
    "compose",
    "--env-file", "config/versions.env",
    "--env-file", "config/defaults.env",
    "-f", "compose.yml"
)

$streamingServices = @(
    "kafka",
    "kafka-init",
    "schema-registry",
    "binance-producer-btcusdc-1s",
    "binance-producer-btcusdc-1m",
    "binance-producer-btcusdc-15m",
    "binance-producer-btcusdc-1h",
    "binance-producer-ethusdc-1s",
    "binance-producer-ethusdc-1m",
    "binance-producer-ethusdc-15m",
    "binance-producer-ethusdc-1h",
    "binance-producer-solusdc-1s",
    "binance-producer-solusdc-1m",
    "binance-producer-solusdc-15m",
    "binance-producer-solusdc-1h"
)

$lakeServices = @(
    "namenode",
    "datanode",
    "hdfs-init",
    "resourcemanager",
    "nodemanager",
    "spark-history"
)

$storageServices = @("postgres")

$warehouseCoreServices = @(
    "hive-schema",
    "hive-metastore",
    "hiveserver2"
)

$warehouseServices = $storageServices + $warehouseCoreServices

$orchestrationCoreServices = @(
    "airflow-image",
    "airflow-db-init",
    "airflow-init",
    "airflow-webserver",
    "airflow-scheduler"
)

$uiServices = @(
    "kafka-ui",
    "hue"
)

$orchestrationServices = $streamingServices + $storageServices + @(
    "namenode",
    "datanode",
    "hdfs-init",
    "resourcemanager",
    "nodemanager"
) + $warehouseCoreServices + $orchestrationCoreServices

$platformServices = $streamingServices + $lakeServices + $warehouseServices + $uiServices
$allServices = $platformServices + $orchestrationCoreServices

$commands = @{
    "streaming-up"  = @("--profile", "ingestion", "up", "-d", "--build") + $streamingServices
    "lake-up"       = @("up", "-d", "--build") + $lakeServices
    "storage-up"    = @("up", "-d", "--build") + $storageServices
    "warehouse-up"  = @("up", "-d", "--build") + $warehouseServices
    "orchestration-up" = @("--profile", "ingestion", "--profile", "orchestration", "up", "-d", "--build") + $orchestrationServices
    "platform-up"   = @("--profile", "ingestion", "--profile", "ui", "up", "-d", "--build") + $platformServices
    "all-up"        = @("--profile", "ingestion", "--profile", "ui", "--profile", "orchestration", "up", "-d", "--build") + $allServices
    "raw-up"        = @("--profile", "tools", "run", "--rm", "--no-deps", "spark-client", "bash", "/workspace/infra/scripts/submit-raw-consumer.sh")
    "raw-stop"      = @("exec", "-T", "resourcemanager", "bash", "/workspace/infra/scripts/stop-yarn-application.sh", "raw-consumer-market-candles")
    "bronze-up"     = @("--profile", "tools", "run", "--rm", "--no-deps", "spark-client", "bash", "/workspace/infra/scripts/submit-bronze.sh")
    "bronze-stop"   = @("exec", "-T", "resourcemanager", "bash", "/workspace/infra/scripts/stop-yarn-application.sh", "bronze-market-candles")
    "status"        = @("--profile", "ingestion", "--profile", "ui", "--profile", "tools", "--profile", "orchestration", "ps")
    "down"          = @("down")
    "ui-up"         = @("--profile", "ui", "up", "-d", "--build") + $uiServices
    "run-silver"    = @("--profile", "tools", "run", "--rm", "--no-deps", "spark-client", "bash", "/workspace/infra/scripts/submit-silver.sh")
    "run-gold"      = @("--profile", "tools", "run", "--rm", "--no-deps", "spark-client", "bash", "/workspace/infra/scripts/submit-gold.sh")
    "run-serving"   = @("--profile", "tools", "run", "--rm", "--no-deps", "spark-client", "bash", "/workspace/infra/scripts/submit-serving.sh")
    "test"          = @("--profile", "tools", "run", "--rm", "--no-deps", "spark-client", "bash", "-lc", "export PYTHONPATH=/workspace:/workspace/jobs:/opt/spark/python:/opt/spark/python/lib/py4j-0.10.9.7-src.zip; cd /workspace; python3 -m unittest discover -s tests -v")
    "config"        = @("config")
}

& docker @compose @($commands[$Action])
exit $LASTEXITCODE
