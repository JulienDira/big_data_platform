# Cadrage Raw vers Bronze

Date: 2026-06-17

Objectif: cadrer le fonctionnement Spark Structured Streaming entre la couche
Raw et la couche Bronze avant d'etendre les changements a Silver puis Gold.

## Positionnement

Le flux cible Raw -> Bronze est un streaming en deux etages avec Raw comme zone
persistante intermediaire:

```text
Kafka
  -> Spark Structured Streaming raw-consumer sur YARN
  -> HDFS Raw Parquet
  -> Spark Structured Streaming bronze-ingestion sur YARN
  -> HDFS Bronze Parquet
```

Bronze ne lit pas directement Kafka dans la cible courante. Il lit Raw depuis
HDFS afin de permettre le rejeu, l'audit et la reconstruction de Bronze sans
dependre de la retention Kafka.

## Contrat Raw

Raw conserve l'envelope Kafka et les metadonnees techniques:

- `topic`, `partition`, `offset`;
- `key`, `value`;
- timestamps Kafka;
- `symbol`, `interval`;
- `ingested_at`;
- partitions `symbol`, `interval`, `ingestion_date`, `ingestion_hour`.

Le champ `value` reste le payload Avro Confluent original. Bronze est
responsable du decodage applicatif.

## Semantique Bronze

Bronze est la premiere couche metier decodee:

- lecture streaming de Raw en Parquet;
- decodage Avro selon `contracts/market-candle/v1.avsc`;
- rejet technique des payloads non decodables vers `KAFKA_ERROR_TOPIC`;
- typage selon le contrat Avro;
- ajout de `event_date`, `year`, `month`, `day`;
- watermark configure par `BRONZE_WATERMARK_DELAY`;
- dedoublonnage minimal par `event_id`;
- ecriture Parquet append-only dans `BRONZE_PATH`;
- partitionnement par `event_date`, `symbol`, `interval`.

Bronze ne porte pas les regles analytiques Silver. Les controles metier plus
forts, la selection de la derniere bougie par cle et les aggregations restent
hors de cette couche.

## Micro-batch

Le job Bronze utilise un trigger explicite configure par:

```text
BRONZE_TRIGGER_INTERVAL=30 seconds
```

Ce choix rend le comportement lisible pour le POC local: Spark reste en
Structured Streaming, mais les traitements sont cadences par micro-batchs
observables et parametrables.

## Rejeu et idempotence

Le checkpoint Bronze est stocke dans `BRONZE_CHECKPOINT_PATH`. Pour rejouer
Bronze depuis Raw, il faut repartir d'un checkpoint Bronze vide ou dedie. Le
resultat logique attendu doit rester stable pour un meme contenu Raw, sous
reserve des regles de watermark et de dedoublonnage.

## Limites POC

- Les erreurs de decodage partent dans Kafka, pas encore dans une zone HDFS
  `rejected`.
- La reprise et le rejeu restent a valider runtime.
- Le delai de watermark est une valeur locale POC a ajuster si les donnees
  arrivent en retard au-dela de la fenetre retenue.
