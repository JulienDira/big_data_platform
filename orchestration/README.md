# Orchestration Airflow

Airflow sert a soumettre les jobs Spark. Les traitements s'executent sur YARN;
Airflow lance les scripts et affiche les logs de soumission.

## DAGs

| DAG | Role |
|---|---|
| `raw_market_candles` | Soumet Raw via `infra/scripts/submit-raw-consumer.sh` |
| `bronze_market_candles` | Soumet Bronze via `infra/scripts/submit-bronze.sh` |
| `market_streaming_submit` | Soumet Raw puis Bronze |
| `silver_market_candles` | Soumet Silver via `infra/scripts/submit-silver.sh` |
| `gold_market_indicators` | Soumet Gold via `infra/scripts/submit-gold.sh` |
| `serving_market_datamart` | Soumet Serving via `infra/scripts/submit-serving.sh` |
| `market_batch_pipeline` | Execute Silver, Gold puis Serving |

Les DAGs sont manuels (`schedule=None`). Raw et Bronze sont des applications
longues: une tache Airflow terminee signifie que la soumission YARN a ete
acceptee, pas que le streaming est termine.

## Commandes

```powershell
.\platform.ps1 orchestration-up
.\platform.ps1 status
```

Equivalent Make:

```bash
make orchestration-up
make status
```

Interface locale:

```text
http://localhost:8080
```

Identifiants locaux:

```text
airflow / airflow
```

## Suivi

- logs de soumission: http://localhost:8080
- applications YARN: http://localhost:8088
- applications Spark terminees: http://localhost:18080

Les scripts evitent de soumettre une application Raw ou Bronze si un job YARN
du meme nom est deja `RUNNING` ou `ACCEPTED`.
