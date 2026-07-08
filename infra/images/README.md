# Images Docker

Les images custom gardent le runtime local reproductible et evitent de
disperser les dependances dans les scripts.

## `big-data-platform/hadoop-runtime`

Base: `apache/hadoop:${HADOOP_VERSION}`.

Utilisee par:

- NameNode;
- DataNode;
- ResourceManager;
- NodeManager;
- initialisation HDFS.

Elle ajoute un runtime Python dans `/opt/conda` pour executer les jobs PySpark
sur les NodeManagers. Les dependances Python sont dans
`infra/images/pyspark-requirements.txt`.

## `big-data-platform/spark-client`

Base: `apache/spark:${SPARK_VERSION}`.

Utilisee pour:

- soumettre les jobs Spark vers YARN;
- lancer Spark History Server.

Elle partage les dependances PySpark avec `hadoop-runtime` et ne lance pas de
cluster Spark standalone.

## `big-data-platform/hive`

Base: `apache/hive:${HIVE_VERSION}`.

Utilisee par:

- initialisation Hive;
- Hive Metastore;
- HiveServer2.

Elle embarque le driver JDBC PostgreSQL compatible avec le metastore local.

## `big-data-platform/airflow-spark`

Base: `apache/airflow:${AIRFLOW_VERSION}` avec Spark copie depuis
`apache/spark:${SPARK_VERSION}`.

Utilisee par:

- Airflow webserver;
- Airflow scheduler;
- initialisation metadata Airflow;
- soumission des jobs Spark depuis les DAGs.

Les configurations Hadoop et Spark sont montees en lecture seule au runtime.
