# Cadrage Gold lake

Date: 2026-06-17

Objectif: materialiser les indicateurs analytiques dans le lake avant toute
projection datamart.

## Role

Gold lake est la couche Hive/HDFS des objets analytiques calcules depuis Silver:

- lecture de `silver.market_candles`;
- calcul par groupe `(symbol, interval)`;
- conservation des colonnes OHLCV utiles;
- calcul EMA 12/26, MACD, RSI 14 et bandes de Bollinger;
- ajout de `event_date`;
- ecriture Parquet dans Hive;
- partitionnement par `event_date`, `symbol`, `interval`;
- rebuild complet deterministe.

Gold lake ne charge pas PostgreSQL directement. PostgreSQL est charge par le job
Serving dedie afin de separer calcul analytique et publication metier.

## Sortie

Table cible:

```text
gold.market_indicators
```

Variables:

```text
GOLD_DATABASE=gold
GOLD_TABLE=market_indicators
```

## Datamart

Les variables `DATAMART_*` de `config/defaults.env` pilotent le chargement vers
PostgreSQL:

```text
DATAMART_JDBC_URL
DATAMART_DB_USER
DATAMART_DB_PASSWORD
DATAMART_INDICATORS_TABLE
DATAMART_LATEST_TABLE
DATAMART_MULTITIMEFRAME_TABLE
DATAMART_DAILY_SUMMARY_TABLE
DATAMART_BASE_INTERVAL
DATAMART_CONTEXT_INTERVALS
```

Le job `jobs/serving-datamart` lit `gold.market_indicators`, applique une
registry SQL et reconstruit les tables PostgreSQL `market_indicators`,
`market_indicators_latest`, `market_multitimeframe_signals` et
`market_daily_summary`.

## Cible AWS

La cible AWS ne publie pas ces tables dans PostgreSQL. Les memes
transformations de restitution sont materialisees en Parquet sur S3 sous une
base logique `trading_gold`, puis exposees par Glue Data Catalog et Athena.
PostgreSQL reste donc une projection on-premise, pas une cible cloud.
