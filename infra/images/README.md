# Images custom

Les images custom existent pour garder une infrastructure Docker Compose locale reproductible, sans disperser les dependances d'execution dans les scripts ou dans les jobs.

## `big-data-platform/hadoop-runtime`

Base: `apache/hadoop:${HADOOP_VERSION}`.

Usage:

- NameNode;
- DataNode;
- ResourceManager;
- NodeManager;
- jobs d'initialisation HDFS.

Justification:

- l'image officielle Hadoop fournit le socle Hadoop/YARN;
- le NodeManager doit disposer d'un runtime Python pour executer les jobs PySpark soumis sur YARN;
- Python est construit dans un stage Miniforge explicite puis copie dans `/opt/conda`, afin d'eviter les paquets Python absents des depots CentOS 7 archives de la base Hadoop;
- les dependances Python sont centralisees dans `infra/images/pyspark-requirements.txt`;
- le runtime Python est explicite et versionne par `MINIFORGE_VERSION` et `PYTHON_VERSION`.

Limite POC:

- le runtime Python depend de l'image `condaforge/miniforge3:${MINIFORGE_VERSION}` au build;
- l'image reste volontairement simple pour le POC local;
- le passage a la production demanderait un durcissement utilisateur non-root, scan d'image et eventuellement digest d'image.

## `big-data-platform/spark-client`

Base: `apache/spark:${SPARK_VERSION}`.

Usage:

- soumission des jobs Spark vers YARN;
- Spark History Server.

Justification:

- separe la soumission Spark des services Hadoop/YARN;
- partage les memes dependances PySpark que `hadoop-runtime`;
- conserve Spark Standalone hors de la cible.

## `big-data-platform/hive`

Base: `apache/hive:${HIVE_VERSION}`.

Usage:

- initialisation schema Hive;
- Hive Metastore;
- HiveServer2.

Justification:

- embarque le driver JDBC PostgreSQL necessaire au metastore Hive;
- retire les anciens jars PostgreSQL de l'image de base avant d'ajouter le driver cible, afin d'eviter que Hive charge un driver incompatible avec PostgreSQL 16;
- evite les montages manuels de driver au runtime.

Limite POC:

- le driver JDBC est telecharge au build;
- avant production, ajouter une verification de checksum ou un artefact interne controle.

## `big-data-platform/airflow-spark`

Base: `apache/airflow:${AIRFLOW_VERSION}` avec Spark copie depuis
`apache/spark:${SPARK_VERSION}`.

Usage:

- Airflow webserver;
- Airflow scheduler;
- initialisation de la base metadata Airflow;
- soumission des batchs Silver et Gold vers YARN depuis les DAGs.

Justification:

- Airflow reste un orchestrateur batch et ne remplace pas YARN;
- les DAGs utilisent les scripts de soumission Spark deja versionnes;
- Spark est present dans l'image Airflow pour eviter un chemin d'execution
  parallele ou une dependance au Docker socket;
- les configurations Hadoop et Spark sont montees en lecture seule au runtime.

Limite POC:

- les identifiants Airflow locaux sont declaratifs dans `defaults.env`;
- l'image doit etre construite et scannee avant tout usage hors POC local.
