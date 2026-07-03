locals {
  glue_databases = {
    raw          = var.raw_database_name
    bronze       = var.bronze_database_name
    silver       = var.silver_database_name
    gold         = var.gold_database_name
    trading_gold = var.trading_gold_database_name
  }

  parquet_table_parameters = {
    EXTERNAL       = "TRUE"
    classification = "parquet"
    typeOfData     = "file"
  }

  projection_event_date = {
    "projection.enabled"                  = "true"
    "projection.event_date.type"          = "date"
    "projection.event_date.format"        = "yyyy-MM-dd"
    "projection.event_date.range"         = var.partition_projection_date_range
    "projection.event_date.interval"      = "1"
    "projection.event_date.interval.unit" = "DAYS"
  }

  projection_symbol = {
    "projection.symbol.type"   = "enum"
    "projection.symbol.values" = join(",", var.partition_projection_symbols)
  }

  projection_interval = {
    "projection.interval.type"   = "enum"
    "projection.interval.values" = join(",", var.partition_projection_intervals)
  }

  projection_ingestion_hour = {
    "projection.ingestion_hour.type"   = "integer"
    "projection.ingestion_hour.range"  = "0,23"
    "projection.ingestion_hour.digits" = "1"
  }

  symbol_interval_ingestion_partitions = [
    { name = "symbol", type = "string" },
    { name = "interval", type = "string" },
    { name = "ingestion_date", type = "date" },
    { name = "ingestion_hour", type = "int" },
  ]

  event_date_symbol_interval_partitions = [
    { name = "event_date", type = "date" },
    { name = "symbol", type = "string" },
    { name = "interval", type = "string" },
  ]

  event_date_symbol_partitions = [
    { name = "event_date", type = "date" },
    { name = "symbol", type = "string" },
  ]

  raw_columns = [
    { name = "source", type = "string" },
    { name = "stream_name", type = "string" },
    { name = "partition_key", type = "string" },
    { name = "sequence_number", type = "string" },
    { name = "approximate_arrival_timestamp", type = "timestamp" },
    { name = "value", type = "binary" },
    { name = "payload_size_bytes", type = "int" },
    { name = "is_avro_decodable", type = "boolean" },
    { name = "ingested_at", type = "timestamp" },
  ]

  bronze_columns = [
    { name = "event_id", type = "string" },
    { name = "source", type = "string" },
    { name = "open_time", type = "timestamp" },
    { name = "close_time", type = "timestamp" },
    { name = "open", type = "double" },
    { name = "high", type = "double" },
    { name = "low", type = "double" },
    { name = "close", type = "double" },
    { name = "volume", type = "double" },
    { name = "quote_asset_volume", type = "double" },
    { name = "number_of_trades", type = "bigint" },
    { name = "taker_buy_base_asset_volume", type = "double" },
    { name = "taker_buy_quote_asset_volume", type = "double" },
    { name = "is_closed", type = "boolean" },
    { name = "ingested_at", type = "timestamp" },
    { name = "year", type = "int" },
    { name = "month", type = "int" },
    { name = "day", type = "int" },
  ]

  silver_columns = [
    { name = "event_id", type = "string" },
    { name = "source", type = "string" },
    { name = "open_time", type = "timestamp" },
    { name = "close_time", type = "timestamp" },
    { name = "open", type = "double" },
    { name = "high", type = "double" },
    { name = "low", type = "double" },
    { name = "close", type = "double" },
    { name = "volume", type = "double" },
    { name = "quote_asset_volume", type = "double" },
    { name = "number_of_trades", type = "bigint" },
    { name = "taker_buy_base_asset_volume", type = "double" },
    { name = "taker_buy_quote_asset_volume", type = "double" },
    { name = "is_closed", type = "boolean" },
    { name = "ingested_at", type = "timestamp" },
  ]

  gold_indicator_columns = [
    { name = "open_time", type = "timestamp" },
    { name = "close_time", type = "timestamp" },
    { name = "open", type = "double" },
    { name = "high", type = "double" },
    { name = "low", type = "double" },
    { name = "close", type = "double" },
    { name = "volume", type = "double" },
    { name = "ema_12", type = "double" },
    { name = "ema_26", type = "double" },
    { name = "macd", type = "double" },
    { name = "rsi_14", type = "double" },
    { name = "bollinger_middle", type = "double" },
    { name = "bollinger_upper", type = "double" },
    { name = "bollinger_lower", type = "double" },
  ]

  latest_indicator_columns = concat(
    [
      { name = "symbol", type = "string" },
      { name = "interval", type = "string" },
    ],
    local.gold_indicator_columns,
    [
      { name = "event_date", type = "date" },
      { name = "updated_at", type = "timestamp" },
    ],
  )

  market_indicator_restitution_columns = concat(
    local.gold_indicator_columns,
    [
      { name = "loaded_at", type = "timestamp" },
    ],
  )

  multitimeframe_signal_columns = [
    { name = "symbol", type = "string" },
    { name = "base_interval", type = "string" },
    { name = "open_time", type = "timestamp" },
    { name = "close_time", type = "timestamp" },
    { name = "close", type = "double" },
    { name = "volume", type = "double" },
    { name = "rsi_14_1m", type = "double" },
    { name = "macd_1m", type = "double" },
    { name = "trend_15m", type = "string" },
    { name = "rsi_14_15m", type = "double" },
    { name = "macd_15m", type = "double" },
    { name = "trend_1h", type = "string" },
    { name = "rsi_14_1h", type = "double" },
    { name = "macd_1h", type = "double" },
    { name = "signal_score", type = "int" },
    { name = "signal_label", type = "string" },
    { name = "generated_at", type = "timestamp" },
  ]

  daily_summary_columns = [
    { name = "open_price", type = "double" },
    { name = "close_price", type = "double" },
    { name = "high_price", type = "double" },
    { name = "low_price", type = "double" },
    { name = "daily_volume", type = "double" },
    { name = "avg_rsi_14", type = "double" },
    { name = "avg_macd", type = "double" },
    { name = "volatility_score", type = "double" },
    { name = "generated_at", type = "timestamp" },
  ]

  date_symbol_interval_projection = merge(
    local.projection_event_date,
    local.projection_symbol,
    local.projection_interval,
  )

  raw_projection = merge(
    {
      "projection.enabled"                      = "true"
      "projection.ingestion_date.type"          = "date"
      "projection.ingestion_date.format"        = "yyyy-MM-dd"
      "projection.ingestion_date.range"         = var.partition_projection_date_range
      "projection.ingestion_date.interval"      = "1"
      "projection.ingestion_date.interval.unit" = "DAYS"
    },
    local.projection_symbol,
    local.projection_interval,
    local.projection_ingestion_hour,
  )

  date_symbol_projection = merge(
    local.projection_event_date,
    local.projection_symbol,
  )

  glue_tables = {
    raw_market_candles = {
      database_key   = "raw"
      name           = "market_candles"
      location       = local.raw_output_path
      columns        = local.raw_columns
      partition_keys = local.symbol_interval_ingestion_partitions
      parameters = merge(
        local.raw_projection,
        {
          "storage.location.template" = "${local.raw_output_path}/symbol=$${symbol}/interval=$${interval}/ingestion_date=$${ingestion_date}/ingestion_hour=$${ingestion_hour}/"
        },
      )
    }

    bronze_market_candles = {
      database_key   = "bronze"
      name           = "market_candles"
      location       = local.bronze_output_path
      columns        = local.bronze_columns
      partition_keys = local.event_date_symbol_interval_partitions
      parameters = merge(
        local.date_symbol_interval_projection,
        {
          "storage.location.template" = "${local.bronze_output_path}/event_date=$${event_date}/symbol=$${symbol}/interval=$${interval}/"
        },
      )
    }

    silver_market_candles = {
      database_key   = "silver"
      name           = "market_candles"
      location       = local.silver_input_path
      columns        = local.silver_columns
      partition_keys = local.event_date_symbol_interval_partitions
      parameters = merge(
        local.date_symbol_interval_projection,
        {
          "storage.location.template" = "${local.silver_input_path}/event_date=$${event_date}/symbol=$${symbol}/interval=$${interval}/"
        },
      )
    }

    gold_market_indicators = {
      database_key   = "gold"
      name           = "market_indicators"
      location       = local.gold_output_path
      columns        = local.gold_indicator_columns
      partition_keys = local.event_date_symbol_interval_partitions
      parameters = merge(
        local.date_symbol_interval_projection,
        {
          "storage.location.template" = "${local.gold_output_path}/event_date=$${event_date}/symbol=$${symbol}/interval=$${interval}/"
        },
      )
    }

    trading_gold_market_indicators = {
      database_key   = "trading_gold"
      name           = "market_indicators"
      location       = "${local.trading_gold_output_base_path}/market_indicators"
      columns        = local.market_indicator_restitution_columns
      partition_keys = local.event_date_symbol_interval_partitions
      parameters = merge(
        local.date_symbol_interval_projection,
        {
          "storage.location.template" = "${local.trading_gold_output_base_path}/market_indicators/event_date=$${event_date}/symbol=$${symbol}/interval=$${interval}/"
        },
      )
    }

    trading_gold_market_indicators_latest = {
      database_key   = "trading_gold"
      name           = "market_indicators_latest"
      location       = "${local.trading_gold_output_base_path}/market_indicators_latest"
      columns        = local.latest_indicator_columns
      partition_keys = []
      parameters     = {}
    }

    trading_gold_market_multitimeframe_signals = {
      database_key   = "trading_gold"
      name           = "market_multitimeframe_signals"
      location       = "${local.trading_gold_output_base_path}/market_multitimeframe_signals"
      columns        = local.multitimeframe_signal_columns
      partition_keys = []
      parameters     = {}
    }

    trading_gold_market_daily_summary = {
      database_key   = "trading_gold"
      name           = "market_daily_summary"
      location       = "${local.trading_gold_output_base_path}/market_daily_summary"
      columns        = local.daily_summary_columns
      partition_keys = local.event_date_symbol_partitions
      parameters = merge(
        local.date_symbol_projection,
        {
          "storage.location.template" = "${local.trading_gold_output_base_path}/market_daily_summary/event_date=$${event_date}/symbol=$${symbol}/"
        },
      )
    }
  }
}

resource "aws_glue_catalog_database" "databases" {
  for_each = local.glue_databases

  name        = each.value
  description = "Data Catalog database for ${local.name_prefix} ${each.key} datasets."
}

resource "aws_glue_catalog_table" "tables" {
  for_each = local.glue_tables

  name          = each.value.name
  database_name = aws_glue_catalog_database.databases[each.value.database_key].name
  table_type    = "EXTERNAL_TABLE"
  parameters    = merge(local.parquet_table_parameters, each.value.parameters)

  storage_descriptor {
    location      = "${each.value.location}/"
    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"

    ser_de_info {
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"

      parameters = {
        "serialization.format" = "1"
      }
    }

    dynamic "columns" {
      for_each = each.value.columns

      content {
        name = columns.value.name
        type = columns.value.type
      }
    }
  }

  dynamic "partition_keys" {
    for_each = each.value.partition_keys

    content {
      name = partition_keys.value.name
      type = partition_keys.value.type
    }
  }
}
