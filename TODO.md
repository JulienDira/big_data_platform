| Besoin du document | Etat actuel | Effort |
|---|---|---:|
| Ingestion Binance en streaming | Partiellement: pipeline Kafka/Spark streaming, mais producer Binance en REST polle, pas WebSocket | Moyen |
| Raw HDFS avec enveloppe Kafka | Oui | Fait |
| Bronze decode/controle | Oui | Fait |
| Silver propre dans Hive | Oui | Fait |
| Gold indicateurs dans Hive | Oui, EMA/MACD/RSI/Bollinger | Fait |
| PostgreSQL serving/datamart on-prem | Oui: job `jobs/serving-datamart`, registry SQL, DAG et commande `run-serving` | Fait |
| Transformations de restitution reutilisables | Oui: extraction dans `jobs/utils/serving.py` | Fait |
| Gold AWS enrichi S3/Athena | Prepare: entry point `jobs/gold-indicators/aws.py`, reste a valider sur AWS | Moyen |
| Multi-timeframe serving | Oui: SQL `market_multitimeframe_signals.sql`, reste preuve runtime end-to-end | Leger |
| Orchestration Airflow | Oui pour Raw/Bronze/Silver/Gold/Serving | Fait |
| Volumetrie/datasets/colonnes | Partiellement documente, a completer avec un golden dataset | Leger |
| Tests/CI/CD Big Data Framework | Tests unitaires partiels, preuve runtime complete encore a faire | Moyen |
| Proxmox/Portainer/preuves infra | Dans le document, mais pas vraiment prouvable par le repo seul | A documenter/capturer |
