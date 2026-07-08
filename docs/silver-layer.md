# Silver

Silver est la table Hive/HDFS des bougies propres. Elle lit Bronze et produit
un jeu de donnees stable pour les calculs analytiques.

## Role

- garder uniquement les candles fermees;
- appliquer les controles OHLCV minimaux;
- dedoublonner par `(symbol, interval, open_time)`;
- conserver la version la plus recente via `ingested_at`;
- departager les doublons restants avec `event_id`;
- partitionner par `event_date`, `symbol`, `interval`.

Silver ne calcule pas EMA, MACD, RSI ou Bollinger. Ces indicateurs sont dans
Gold.

## Sortie

```text
silver.market_candles
```

Colonnes principales:

- provenance: `event_id`, `source`, `ingested_at`;
- marche: `symbol`, `interval`, `open_time`, `close_time`;
- OHLCV: `open`, `high`, `low`, `close`, `volume`;
- volumes complementaires: `quote_asset_volume`, `number_of_trades`,
  `taker_buy_base_asset_volume`, `taker_buy_quote_asset_volume`;
- controle: `is_closed`;
- partition: `event_date`.

Le job `jobs/silver-transformation` reconstruit la table de facon
deterministe.
