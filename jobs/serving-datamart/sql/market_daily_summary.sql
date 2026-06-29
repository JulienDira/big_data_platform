WITH base AS (
  SELECT *
  FROM {{source_view}}
  WHERE interval = '{{base_interval}}'
),
ranked AS (
  SELECT
    *,
    row_number() OVER (
      PARTITION BY symbol, event_date
      ORDER BY open_time ASC
    ) AS first_row,
    row_number() OVER (
      PARTITION BY symbol, event_date
      ORDER BY open_time DESC
    ) AS last_row
  FROM base
)
SELECT
  symbol,
  event_date,
  max(CASE WHEN first_row = 1 THEN open END) AS open_price,
  max(CASE WHEN last_row = 1 THEN close END) AS close_price,
  max(high) AS high_price,
  min(low) AS low_price,
  sum(volume) AS daily_volume,
  avg(rsi_14) AS avg_rsi_14,
  avg(macd) AS avg_macd,
  coalesce(stddev(close), 0.0) AS volatility_score,
  current_timestamp() AS generated_at
FROM ranked
GROUP BY symbol, event_date

