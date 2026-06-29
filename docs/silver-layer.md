# Cadrage Silver

Date: 2026-06-17

Objectif: fixer le role de Silver avant de faire evoluer Gold et le datamart.

## Role

Silver est la couche Hive/HDFS des candles propres:

- donnees decodees depuis Bronze;
- candles fermees uniquement;
- colonnes stables et explicites;
- controles qualite OHLCV minimaux;
- dedoublonnage par `(symbol, interval, open_time)`;
- conservation de la version la plus recente via `ingested_at`;
- tie-break deterministe par `event_id`;
- partitionnement par `event_date`, `symbol`, `interval`.

Silver ne calcule pas les indicateurs EMA, MACD, RSI ou Bollinger. Ces
indicateurs sont des objets analytiques et appartiennent a une couche Gold lake
ou a une couche metier ulterieure.

## Sortie

Table cible:

```text
silver.market_candles
```

Colonnes conservees:

- identite et provenance: `event_id`, `source`;
- cle marche: `symbol`, `interval`, `open_time`, `close_time`;
- OHLCV: `open`, `high`, `low`, `close`, `volume`,
  `quote_asset_volume`, `number_of_trades`,
  `taker_buy_base_asset_volume`, `taker_buy_quote_asset_volume`;
- controle: `is_closed`;
- audit: `ingested_at`;
- partition metier: `event_date`.

## Evolution attendue

La prochaine etape doit separer:

```text
Silver clean candles
  -> Gold lake indicators / aggregates
  -> PostgreSQL datamart or serving tables
```

PostgreSQL ne doit plus etre considere comme la couche Gold principale lorsque
la couche Gold lake est introduite. Il devient une projection optimisee pour la
consultation metier.
