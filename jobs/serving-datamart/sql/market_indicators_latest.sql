WITH ranked AS (
  SELECT
    *,
    row_number() OVER (
      PARTITION BY symbol, interval
      ORDER BY open_time DESC
    ) AS row_number
  FROM {{source_view}}
)
SELECT
  symbol,
  interval,
  open_time,
  close_time,
  open,
  high,
  low,
  close,
  volume,
  ema_12,
  ema_26,
  macd,
  rsi_14,
  bollinger_middle,
  bollinger_upper,
  bollinger_lower,
  event_date,
  current_timestamp() AS updated_at
FROM ranked
WHERE row_number = 1

