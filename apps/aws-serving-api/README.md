# AWS Serving API

Static/local implementation for the AWS restitution exposure layer.

## Scope

- `api_handler.py`: read-only Lambda handler for:
  - `GET /health`
  - `GET /metrics/latest`
  - `GET /metrics/history`
  - `GET /signals`
  - `GET /daily-summary`
- `projection_handler.py`: dedicated latest metrics projection from
  `trading_gold.market_indicators_latest` to DynamoDB.
- `common.py`: pure validation, response and DynamoDB/Athena mapping helpers.

The API Lambda does not compute EMA, MACD, RSI or Bollinger, and it does not
write lake datasets. The projection Lambda writes only the DynamoDB latest
cache keyed by `(symbol, interval)`.
