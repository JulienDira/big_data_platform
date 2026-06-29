# Orchestration Airflow

Airflow sert de point de soumission manuel pour les jobs Spark du POC local.
Raw et Bronze restent des applications Spark Structured Streaming executees par
YARN; Airflow ne fait que lancer `spark-submit`.

## DAGs

| DAG | Role |
|---|---|
| `raw_market_candles` | Soumet le streaming Raw vers YARN via `infra/scripts/submit-raw-consumer.sh` |
| `bronze_market_candles` | Soumet le streaming Bronze vers YARN via `infra/scripts/submit-bronze.sh` |
| `market_streaming_submit` | Soumet Raw puis Bronze dans le bon ordre |
| `silver_market_candles` | Soumet le batch Silver vers YARN via `infra/scripts/submit-silver.sh` |
| `gold_market_indicators` | Soumet le batch Gold vers YARN via `infra/scripts/submit-gold.sh` |
| `serving_market_datamart` | Soumet le batch Serving PostgreSQL via `infra/scripts/submit-serving.sh` |
| `market_batch_pipeline` | Orchestre Silver puis Gold puis Serving dans le bon ordre |

Les DAGs sont manuels (`schedule=None`) pour garder le POC explicite. Les DAGs
Raw et Bronze soumettent des applications longues: une tache Airflow terminee
signifie que la soumission YARN a ete acceptee, pas que le streaming est fini.
Les scripts de soumission evitent de relancer une application si un job YARN du
meme nom est deja `RUNNING` ou `ACCEPTED`.
Ajouter une planification horaire ou quotidienne seulement quand les volumes
Raw/Bronze et les fenetres de recalcul sont stabilises.

## Commandes

```bash
make orchestration-up
make status
```

Interface Airflow locale:

```text
http://localhost:8080
```

Identifiants POC:

```text
airflow / airflow
```

## Logs

Airflow affiche les logs de la tache `BashOperator`, donc la sortie de
`spark-submit` et les informations de soumission YARN. Les logs continus des
applications Spark Raw/Bronze sont produits par YARN, car l'execution reelle se
fait dans le cluster YARN.

Pour suivre l'execution apres soumission:

- YARN ResourceManager: http://localhost:8088
- Spark History Server pour les applications terminees: http://localhost:18080
- logs Airflow: http://localhost:8080

Ces identifiants sont acceptables uniquement en local. Airflow utilise le meme
PostgreSQL local que la plateforme, mais avec une base metadata separee
`airflow`. Le service `airflow-db-init` cree cette base de facon idempotente,
y compris si le volume PostgreSQL local existait avant l'ajout d'Airflow.
