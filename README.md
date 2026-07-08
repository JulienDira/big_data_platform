# Big Data Trading Platform

Plateforme data locale pour ingerer des candles Binance, les traiter avec
Spark/YARN et exposer des indicateurs de marche.

Le projet garde une stack on-premise fonctionnelle et prepare une cible AWS
equivalente, sans migration big bang.

## Architecture

```text
Binance REST
-> Kafka + Schema Registry
-> Raw HDFS
-> Bronze HDFS
-> Silver Hive
-> Gold Hive
-> Serving PostgreSQL
```

La cible AWS reprend les memes couches:

```text
Binance
-> Kinesis
-> Raw/Bronze/Silver/Gold sur S3
-> Glue Data Catalog + Athena
-> DynamoDB latest metrics + API Gateway/Lambda + Streamlit
```

PostgreSQL reste uniquement la cible Serving locale. Il n'y a pas de cible RDS
ou PostgreSQL cote AWS.

## Structure

| Chemin | Role |
|---|---|
| `apps/binance-producer` | Producteur Binance local Kafka et entree AWS Kinesis |
| `apps/aws-serving-api` | Lambda API et projection latest metrics |
| `apps/streamlit-dashboard` | Dashboard Streamlit consommant l'API |
| `contracts` | Contrat Avro des candles |
| `config` | Variables locales, versions, chemins et tables |
| `jobs` | Jobs Spark par etape de pipeline |
| `jobs/utils` | Logique partagee: schemas, qualite, indicateurs, IO |
| `orchestration` | DAGs Airflow locaux |
| `infra/compose` | Stack Docker Compose locale |
| `infra/aws` | Stacks Terraform AWS |
| `tests` | Tests unitaires, contrats et garde-fous |
| `docs` | Documentation de couches et cible AWS |

Convention des jobs:

```text
jobs/<etape>/main.py  # execution locale/on-premise
jobs/<etape>/aws.py   # execution AWS quand elle existe
```

## Prerequis

- Docker Desktop avec Docker Compose 2.24+
- 10 GB de memoire Docker recommandes
- PowerShell sur Windows, ou Make via WSL/Git Bash
- Acces internet au premier build d'images

## Demarrage local

PowerShell:

```powershell
.\platform.ps1 help
.\platform.ps1 platform-up
.\platform.ps1 status
.\platform.ps1 raw-up
.\platform.ps1 bronze-up
```

Make:

```bash
make help
make platform-up
make status
make raw-up
make bronze-up
```

Quand Bronze contient des donnees:

```powershell
.\platform.ps1 run-silver
.\platform.ps1 run-gold
.\platform.ps1 run-serving
```

Arret des streams:

```powershell
.\platform.ps1 raw-stop
.\platform.ps1 bronze-stop
```

Validation locale:

```powershell
.\platform.ps1 test
```

Si la politique PowerShell bloque le script:

```powershell
powershell -ExecutionPolicy Bypass -File .\platform.ps1 test
```

## Services locaux

| Service | URL |
|---|---|
| HDFS NameNode | http://localhost:9870 |
| YARN ResourceManager | http://localhost:8088 |
| Spark History Server | http://localhost:18080 |
| Schema Registry | http://localhost:8081 |
| Kafka UI | http://localhost:8085 |
| Hue | http://localhost:8888 |
| Airflow | http://localhost:8080 |

Airflow est optionnel. Il soumet les memes scripts Spark que les commandes
locales, mais YARN reste la surface d'execution reelle.

## Donnees

| Element | Valeur |
|---|---|
| Topic Kafka | `market.candles.v1` |
| Cle Kafka/Kinesis | `symbol|interval` |
| Symboles | `BTCUSDC`, `ETHUSDC`, `SOLUSDC` |
| Intervalles | `1s`, `1m`, `15m`, `1h` |
| Raw HDFS | `/data/raw/binance/market_candles` |
| Bronze HDFS | `/data/bronze/market_candles` |
| Silver Hive | `silver.market_candles` |
| Gold Hive | `gold.market_indicators` |
| Serving PostgreSQL | `trading_gold.*` |

Raw garde l'enveloppe technique. Bronze decode et filtre les erreurs
techniques. Silver conserve les candles fermees, typees et dedupliquees. Gold
calcule EMA, MACD, RSI et Bollinger. Serving reconstruit les tables
PostgreSQL de consultation.

## Documentation utile

- [cadrage.md](cadrage.md): synthese d'architecture et regles de projet.
- [jobs/README.md](jobs/README.md): role des jobs Spark.
- [docs/raw-to-bronze-streaming.md](docs/raw-to-bronze-streaming.md): regles Raw et Bronze.
- [docs/silver-layer.md](docs/silver-layer.md): regles Silver.
- [docs/gold-layer.md](docs/gold-layer.md): regles Gold et Serving.
- [docs/aws-target.md](docs/aws-target.md): cible AWS et etat de preparation.
- [infra/aws/README.md](infra/aws/README.md): deploiement AWS.
