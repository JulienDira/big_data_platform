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
  current_timestamp() AS loaded_at
FROM {{source_view}}

