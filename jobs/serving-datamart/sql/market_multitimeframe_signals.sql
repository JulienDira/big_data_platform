WITH base AS (
  SELECT
    symbol,
    open_time,
    close_time,
    close,
    volume,
    rsi_14,
    macd
  FROM {{source_view}}
  WHERE interval = '{{base_interval}}'
),
context_1_candidates AS (
  SELECT
    b.symbol,
    b.open_time,
    c.rsi_14 AS rsi_14_context_1,
    c.macd AS macd_context_1,
    CASE
      WHEN c.close > c.ema_26 THEN 'up'
      WHEN c.close < c.ema_26 THEN 'down'
      ELSE 'neutral'
    END AS trend_context_1,
    row_number() OVER (
      PARTITION BY b.symbol, b.open_time
      ORDER BY c.open_time DESC
    ) AS row_number
  FROM base b
  LEFT JOIN {{source_view}} c
    ON c.symbol = b.symbol
   AND c.interval = '{{context_interval_1}}'
   AND c.open_time <= b.open_time
),
context_1 AS (
  SELECT
    symbol,
    open_time,
    rsi_14_context_1,
    macd_context_1,
    trend_context_1
  FROM context_1_candidates
  WHERE row_number = 1
),
context_2_candidates AS (
  SELECT
    b.symbol,
    b.open_time,
    c.rsi_14 AS rsi_14_context_2,
    c.macd AS macd_context_2,
    CASE
      WHEN c.close > c.ema_26 THEN 'up'
      WHEN c.close < c.ema_26 THEN 'down'
      ELSE 'neutral'
    END AS trend_context_2,
    row_number() OVER (
      PARTITION BY b.symbol, b.open_time
      ORDER BY c.open_time DESC
    ) AS row_number
  FROM base b
  LEFT JOIN {{source_view}} c
    ON c.symbol = b.symbol
   AND c.interval = '{{context_interval_2}}'
   AND c.open_time <= b.open_time
),
context_2 AS (
  SELECT
    symbol,
    open_time,
    rsi_14_context_2,
    macd_context_2,
    trend_context_2
  FROM context_2_candidates
  WHERE row_number = 1
),
scored AS (
  SELECT
    b.symbol,
    '{{base_interval}}' AS base_interval,
    b.open_time,
    b.close_time,
    b.close,
    b.volume,
    b.rsi_14 AS rsi_14_1m,
    b.macd AS macd_1m,
    c1.trend_context_1 AS trend_15m,
    c1.rsi_14_context_1 AS rsi_14_15m,
    c1.macd_context_1 AS macd_15m,
    c2.trend_context_2 AS trend_1h,
    c2.rsi_14_context_2 AS rsi_14_1h,
    c2.macd_context_2 AS macd_1h,
    (
      CASE WHEN b.macd > 0 THEN 1 WHEN b.macd < 0 THEN -1 ELSE 0 END
      + CASE WHEN c1.macd_context_1 > 0 THEN 1 WHEN c1.macd_context_1 < 0 THEN -1 ELSE 0 END
      + CASE WHEN c2.macd_context_2 > 0 THEN 1 WHEN c2.macd_context_2 < 0 THEN -1 ELSE 0 END
    ) AS signal_score
  FROM base b
  LEFT JOIN context_1 c1
    ON c1.symbol = b.symbol
   AND c1.open_time = b.open_time
  LEFT JOIN context_2 c2
    ON c2.symbol = b.symbol
   AND c2.open_time = b.open_time
)
SELECT
  symbol,
  base_interval,
  open_time,
  close_time,
  close,
  volume,
  rsi_14_1m,
  macd_1m,
  trend_15m,
  rsi_14_15m,
  macd_15m,
  trend_1h,
  rsi_14_1h,
  macd_1h,
  signal_score,
  CASE
    WHEN signal_score >= 2 THEN 'bullish'
    WHEN signal_score <= -2 THEN 'bearish'
    ELSE 'neutral'
  END AS signal_label,
  current_timestamp() AS generated_at
FROM scored

