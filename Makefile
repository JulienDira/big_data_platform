COMPOSE = docker compose --env-file config/versions.env --env-file config/defaults.env -f compose.yml
UP_FLAGS = up -d --build
SPARK_CLIENT_RUN = $(COMPOSE) --profile tools run --rm --no-deps spark-client
YARN_EXEC = $(COMPOSE) exec -T resourcemanager
RAW_APP_NAME = raw-consumer-market-candles
BRONZE_APP_NAME = bronze-market-candles

.DEFAULT_GOAL = help

STREAMING_SERVICES = \
	kafka \
	kafka-init \
	schema-registry \
	binance-producer-btcusdc-1s \
	binance-producer-btcusdc-1m \
	binance-producer-btcusdc-15m \
	binance-producer-btcusdc-1h \
	binance-producer-ethusdc-1s \
	binance-producer-ethusdc-1m \
	binance-producer-ethusdc-15m \
	binance-producer-ethusdc-1h \
	binance-producer-solusdc-1s \
	binance-producer-solusdc-1m \
	binance-producer-solusdc-15m \
	binance-producer-solusdc-1h

LAKE_SERVICES = \
	namenode \
	datanode \
	hdfs-init \
	resourcemanager \
	nodemanager \
	spark-history

STORAGE_SERVICES = \
	postgres

WAREHOUSE_CORE_SERVICES = \
	hive-schema \
	hive-metastore \
	hiveserver2

WAREHOUSE_SERVICES = \
	$(STORAGE_SERVICES) \
	$(WAREHOUSE_CORE_SERVICES)

ORCHESTRATION_CORE_SERVICES = \
	airflow-image \
	airflow-db-init \
	airflow-init \
	airflow-webserver \
	airflow-scheduler

UI_SERVICES = \
	kafka-ui \
	hue

ORCHESTRATION_SERVICES = \
	$(STREAMING_SERVICES) \
	$(STORAGE_SERVICES) \
	namenode \
	datanode \
	hdfs-init \
	resourcemanager \
	nodemanager \
	$(WAREHOUSE_CORE_SERVICES) \
	$(ORCHESTRATION_CORE_SERVICES)

PLATFORM_SERVICES = \
	$(STREAMING_SERVICES) \
	$(LAKE_SERVICES) \
	$(WAREHOUSE_SERVICES) \
	$(UI_SERVICES)

ALL_SERVICES = \
	$(PLATFORM_SERVICES) \
	$(ORCHESTRATION_CORE_SERVICES)

.PHONY: help streaming-up lake-up storage-up warehouse-up orchestration-up ui-up platform-up all-up raw-up raw-stop bronze-up bronze-stop status down run-silver run-gold run-serving test config

help:
	@printf "%s\n" "Big Data Platform commands"
	@printf "%s\n" ""
	@printf "%-22s %s\n" "make streaming-up" "Start Kafka, Schema Registry and Binance producers."
	@printf "%-22s %s\n" "make lake-up" "Start HDFS, YARN and Spark History."
	@printf "%-22s %s\n" "make storage-up" "Start PostgreSQL."
	@printf "%-22s %s\n" "make warehouse-up" "Start storage plus Hive Metastore and HiveServer2."
	@printf "%-22s %s\n" "make orchestration-up" "Start streaming, lake, warehouse and Airflow."
	@printf "%-22s %s\n" "make ui-up" "Start Kafka UI and Hue."
	@printf "%-22s %s\n" "make platform-up" "Start the standard local platform without Airflow."
	@printf "%-22s %s\n" "make all-up" "Start the standard platform plus Airflow."
	@printf "%-22s %s\n" "make raw-up" "Submit the Raw Spark streaming consumer to YARN."
	@printf "%-22s %s\n" "make raw-stop" "Stop the Raw Spark streaming consumer in YARN."
	@printf "%-22s %s\n" "make bronze-up" "Submit the Bronze Spark streaming job to YARN."
	@printf "%-22s %s\n" "make bronze-stop" "Stop the Bronze Spark streaming job in YARN."
	@printf "%-22s %s\n" "make status" "Show Compose service status."
	@printf "%-22s %s\n" "make down" "Stop and remove Compose containers."
	@printf "%-22s %s\n" "make run-silver" "Run the Silver batch job."
	@printf "%-22s %s\n" "make run-gold" "Run the Gold batch job."
	@printf "%-22s %s\n" "make run-serving" "Run the PostgreSQL Serving datamart job."
	@printf "%-22s %s\n" "make test" "Run the platform unit tests."
	@printf "%-22s %s\n" "make config" "Render the resolved Docker Compose config."

streaming-up:
	$(COMPOSE) --profile ingestion $(UP_FLAGS) $(STREAMING_SERVICES)

lake-up:
	$(COMPOSE) $(UP_FLAGS) $(LAKE_SERVICES)

storage-up:
	$(COMPOSE) $(UP_FLAGS) $(STORAGE_SERVICES)

warehouse-up:
	$(COMPOSE) $(UP_FLAGS) $(WAREHOUSE_SERVICES)

orchestration-up:
	$(COMPOSE) --profile ingestion --profile orchestration $(UP_FLAGS) $(ORCHESTRATION_SERVICES)

platform-up:
	$(COMPOSE) --profile ingestion --profile ui $(UP_FLAGS) $(PLATFORM_SERVICES)

all-up:
	$(COMPOSE) --profile ingestion --profile ui --profile orchestration $(UP_FLAGS) $(ALL_SERVICES)

raw-up:
	$(SPARK_CLIENT_RUN) bash /workspace/infra/scripts/submit-raw-consumer.sh

raw-stop:
	$(YARN_EXEC) bash /workspace/infra/scripts/stop-yarn-application.sh $(RAW_APP_NAME)

bronze-up:
	$(SPARK_CLIENT_RUN) bash /workspace/infra/scripts/submit-bronze.sh

bronze-stop:
	$(YARN_EXEC) bash /workspace/infra/scripts/stop-yarn-application.sh $(BRONZE_APP_NAME)

status:
	$(COMPOSE) --profile ingestion --profile ui --profile tools --profile orchestration ps

down:
	$(COMPOSE) down

ui-up:
	$(COMPOSE) --profile ui $(UP_FLAGS) $(UI_SERVICES)

run-silver:
	$(SPARK_CLIENT_RUN) bash /workspace/infra/scripts/submit-silver.sh

run-gold:
	$(SPARK_CLIENT_RUN) bash /workspace/infra/scripts/submit-gold.sh

run-serving:
	$(SPARK_CLIENT_RUN) bash /workspace/infra/scripts/submit-serving.sh

test:
	$(COMPOSE) --profile tools run --rm --no-deps spark-client \
		python3 -m unittest discover -s /workspace/tests -v

config:
	$(COMPOSE) config
