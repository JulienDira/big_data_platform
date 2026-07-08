# Raw vers Bronze

Raw et Bronze sont deux jobs Spark Structured Streaming distincts, executes sur
YARN.

```text
Kafka
  -> raw-consumer
  -> HDFS Raw Parquet
  -> bronze-ingestion
  -> HDFS Bronze Parquet
```

## Raw

Raw stocke l'enveloppe Kafka telle qu'elle arrive:

- `topic`, `partition`, `offset`;
- `key`, `value`;
- timestamps Kafka;
- `symbol`, `interval`;
- `ingested_at`;
- partitions `symbol`, `interval`, `ingestion_date`, `ingestion_hour`.

Le champ `value` reste le payload Avro Confluent. Raw sert de zone de reprise:
Bronze relit HDFS au lieu de relire directement Kafka.

## Bronze

Bronze produit les premieres donnees metier decodees:

- lecture streaming de Raw en Parquet;
- decodage avec `contracts/market-candle/v1.avsc`;
- rejet des payloads non decodables vers `KAFKA_ERROR_TOPIC`;
- typage des colonnes selon le contrat Avro;
- ajout de `event_date`, `year`, `month`, `day`;
- watermark via `BRONZE_WATERMARK_DELAY`;
- dedoublonnage par `event_id`;
- ecriture Parquet dans `BRONZE_PATH`;
- partitionnement par `event_date`, `symbol`, `interval`.

Bronze ne calcule pas d'indicateurs et ne choisit pas la derniere bougie par
cle marche. Ces regles appartiennent a Silver et Gold.

## Parametres utiles

```text
BRONZE_TRIGGER_INTERVAL=30 seconds
BRONZE_WATERMARK_DELAY=2 days
BRONZE_CHECKPOINT_PATH
BRONZE_PATH
KAFKA_ERROR_TOPIC
```

Pour rejouer Bronze depuis Raw, utiliser un checkpoint Bronze vide ou dedie.
