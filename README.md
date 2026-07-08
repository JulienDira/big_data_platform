# Big Data Trading Platform

Plateforme locale de streaming et de traitement batch pour des bougies de
marche Binance. Le projet regroupe l'ingestion, le stockage lake, les
transformations Spark et une projection PostgreSQL de consultation.

## Architecture

```text
Binance REST
  -> producer Avro
  -> Kafka + Schema Registry
  -> Raw HDFS
  -> Bronze HDFS
  -> Silver Hive
  -> Gold Hive
  -> Serving PostgreSQL
```

Spark s'execute sur YARN. Airflow peut soumettre les jobs, mais YARN reste le
runtime des traitements Raw, Bronze, Silver, Gold et Serving.

## Structure

| Dossier | Role |
|---|---|
| `apps/binance-producer` | Producteurs Binance vers Kafka |
| `contracts` | Contrat Avro des candles |
| `config` | Variables locales et versions d'images |
| `infra/compose` | Services Docker Compose |
| `infra/scripts` | Scripts de soumission Spark et init |
| `infra/images` | Images Docker custom |
| `jobs` | Jobs Spark Raw, Bronze, Silver, Gold et Serving |
| `orchestration/dags` | DAGs Airflow de soumission |
| `docs` | Notes courtes par couche de donnees |
| `tests` | Tests unitaires et statiques |

## Prerequis

- Docker Desktop avec Docker Compose 2.24 ou plus recent
- 10 Go de memoire Docker minimum
- PowerShell sur Windows, ou Make via WSL/Git Bash
- Acces internet au premier build des images

## Commandes principales

PowerShell:

```powershell
.\platform.ps1 help
.\platform.ps1 platform-up
.\platform.ps1 status
.\platform.ps1 raw-up
.\platform.ps1 bronze-up
.\platform.ps1 run-silver
.\platform.ps1 run-gold
.\platform.ps1 run-serving
.\platform.ps1 test
```

Make:

```bash
make help
make platform-up
make status
make raw-up
make bronze-up
make run-silver
make run-gold
make run-serving
make test
```

Arret des streamings:

```powershell
.\platform.ps1 raw-stop
.\platform.ps1 bronze-stop
```

Airflow:

```powershell
.\platform.ps1 orchestration-up
```

Les DAGs utiles sont `market_streaming_submit` pour Raw puis Bronze, et
`market_batch_pipeline` pour Silver puis Gold puis Serving.

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

Identifiants Airflow locaux: `airflow` / `airflow`.

## Configuration

- `config/defaults.env`: valeurs locales par defaut
- `config/versions.env`: versions des images et composants
- `config/local.env`: surcharge locale ignoree par Git
- `contracts/market-candle/v1.avsc`: schema Avro canonique

Les producteurs sont declares dans `infra/compose/streaming.yml`. Les flux de
depart couvrent `BTCUSDC`, `ETHUSDC` et `SOLUSDC` sur `1s`, `1m`, `15m` et
`1h`.

## Donnees

| Element | Valeur |
|---|---|
| Topic Kafka | `market.candles.v1` |
| Cle Kafka | `symbol|interval` |
| Topic erreurs | `market.candles.v1.errors` |
| Raw HDFS | `/data/raw/binance/market_candles` |
| Bronze HDFS | `/data/bronze/market_candles` |
| Table Silver | `silver.market_candles` |
| Table Gold | `gold.market_indicators` |
| Tables Serving | `trading_gold.market_indicators`, `trading_gold.market_indicators_latest`, `trading_gold.market_multitimeframe_signals`, `trading_gold.market_daily_summary` |

Raw conserve l'enveloppe Kafka. Bronze decode le payload Avro et applique les
premiers controles techniques. Silver garde les bougies fermees, typees et
dedoublonnees. Gold calcule EMA, MACD, RSI et Bollinger. Serving reconstruit
les tables PostgreSQL de consultation depuis Gold.

## Documentation

- `docs/raw-to-bronze-streaming.md`: regles Raw et Bronze
- `docs/silver-layer.md`: table Silver et qualite minimale
- `docs/gold-layer.md`: indicateurs Gold et projection Serving
- `jobs/README.md`: role des jobs Spark
- `orchestration/README.md`: DAGs Airflow
- `infra/images/README.md`: images Docker custom
