# Gold et Serving

Gold contient les indicateurs analytiques calcules depuis Silver. Serving publie
des tables PostgreSQL plus pratiques a consulter.

## Gold

Le job `jobs/gold-indicators` lit:

```text
silver.market_candles
```

Il ecrit:

```text
gold.market_indicators
```

Indicateurs calcules par `(symbol, interval)`:

- EMA 12 et EMA 26;
- MACD;
- RSI 14;
- bandes de Bollinger.

La sortie conserve les colonnes OHLCV utiles et partitionne par `event_date`,
`symbol`, `interval`. Le rebuild est complet et deterministe.

## Serving

Le job `jobs/serving-datamart` lit `gold.market_indicators`, applique les SQL
de `jobs/serving-datamart/sql` et reconstruit les tables PostgreSQL:

- `market_indicators`;
- `market_indicators_latest`;
- `market_multitimeframe_signals`;
- `market_daily_summary`.

Les noms de tables et la connexion JDBC sont pilotes par les variables
`DATAMART_*` dans `config/defaults.env`.
