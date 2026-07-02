data "aws_caller_identity" "current" {}

data "aws_partition" "current" {}

data "aws_region" "current" {}

locals {
  repo_root    = abspath("${path.module}/../../..")
  project_slug = lower(replace(var.project_name, "_", "-"))
  env_slug     = lower(replace(var.environment, "_", "-"))
  name_prefix  = "${local.project_slug}-${local.env_slug}"

  api_lambda_name        = "${local.name_prefix}-market-api"
  projection_lambda_name = "${local.name_prefix}-latest-metrics-projection"
  api_gateway_name       = "${local.name_prefix}-market-api"
  api_stage_name         = "$default"
  user_pool_name         = "${local.name_prefix}-users"
  cognito_domain_prefix  = coalesce(var.cognito_domain_prefix, "${local.name_prefix}-auth")
  latest_table_name      = coalesce(var.latest_metrics_table_name, "${local.name_prefix}-latest-metrics")

  athena_results_prefix     = trim(var.athena_results_prefix, "/")
  lake_bucket_arn           = "arn:${data.aws_partition.current.partition}:s3:::${var.lake_bucket_name}"
  athena_results_bucket_arn = "arn:${data.aws_partition.current.partition}:s3:::${var.athena_results_bucket_name}"

  market_candles_stream_name = coalesce(var.market_candles_stream_name, "${local.name_prefix}-market-candles")
  ecs_cluster_name           = coalesce(var.ecs_cluster_name, "${local.name_prefix}-producer")
  ecs_service_name           = coalesce(var.ecs_service_name, "${local.name_prefix}-binance-producer")
  default_glue_job_names = [
    "${local.name_prefix}-raw-market-candles-streaming",
    "${local.name_prefix}-bronze-market-candles-batch",
    "${local.name_prefix}-silver-market-candles-batch",
    "${local.name_prefix}-gold-indicators-batch",
  ]
  effective_glue_job_names = length(var.glue_job_names) > 0 ? var.glue_job_names : local.default_glue_job_names
  lambda_package_s3_inputs = [
    for value in [
      var.lambda_package_s3_bucket,
      var.lambda_package_s3_key,
      var.lambda_package_source_hash,
    ] : value if value != null && value != ""
  ]
  lambda_uses_s3_package = length(local.lambda_package_s3_inputs) == 3

  lambda_environment = {
    ALLOWED_INTERVALS            = join(",", var.allowed_intervals)
    ALLOWED_SYMBOLS              = join(",", var.allowed_symbols)
    ATHENA_DATABASE              = var.trading_gold_database_name
    ATHENA_OUTPUT_LOCATION       = var.athena_output_location
    ATHENA_QUERY_TIMEOUT_SECONDS = tostring(var.api_lambda_timeout_seconds - 5)
    ATHENA_WORKGROUP             = var.athena_workgroup_name
    AWS_REGION                   = var.aws_region
    DYNAMODB_TABLE_NAME          = aws_dynamodb_table.latest_metrics.name
    HISTORY_DEFAULT_LIMIT        = tostring(var.history_default_limit)
    HISTORY_MAX_LIMIT            = tostring(var.history_max_limit)
  }
}

data "archive_file" "aws_serving_api" {
  count = local.lambda_uses_s3_package ? 0 : 1

  type        = "zip"
  source_dir  = "${local.repo_root}/apps/aws-serving-api"
  output_path = "${path.module}/.terraform/aws-serving-api.zip"
}

resource "aws_dynamodb_table" "latest_metrics" {
  name         = local.latest_table_name
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "symbol"
  range_key    = "interval"

  attribute {
    name = "symbol"
    type = "S"
  }

  attribute {
    name = "interval"
    type = "S"
  }

  ttl {
    attribute_name = "expires_at_epoch"
    enabled        = var.latest_metrics_ttl_enabled
  }

  server_side_encryption {
    enabled = true
  }
}

resource "aws_cloudwatch_log_group" "api_lambda" {
  name              = "/aws/lambda/${local.api_lambda_name}"
  retention_in_days = var.cloudwatch_log_retention_days
}

resource "aws_cloudwatch_log_group" "projection_lambda" {
  name              = "/aws/lambda/${local.projection_lambda_name}"
  retention_in_days = var.cloudwatch_log_retention_days
}

resource "aws_cloudwatch_log_group" "api_gateway" {
  name              = "/aws/apigateway/${local.api_gateway_name}"
  retention_in_days = var.cloudwatch_log_retention_days
}

resource "aws_lambda_function" "api" {
  function_name    = local.api_lambda_name
  filename         = local.lambda_uses_s3_package ? null : data.archive_file.aws_serving_api[0].output_path
  s3_bucket        = local.lambda_uses_s3_package ? var.lambda_package_s3_bucket : null
  s3_key           = local.lambda_uses_s3_package ? var.lambda_package_s3_key : null
  source_code_hash = local.lambda_uses_s3_package ? var.lambda_package_source_hash : data.archive_file.aws_serving_api[0].output_base64sha256
  handler          = "api_handler.lambda_handler"
  runtime          = var.lambda_runtime
  role             = aws_iam_role.api_lambda.arn
  timeout          = var.api_lambda_timeout_seconds
  memory_size      = var.lambda_memory_mb

  environment {
    variables = local.lambda_environment
  }

  depends_on = [
    aws_cloudwatch_log_group.api_lambda,
    aws_iam_role_policy_attachment.api_lambda,
  ]

  lifecycle {
    precondition {
      condition     = length(local.lambda_package_s3_inputs) == 0 || local.lambda_uses_s3_package
      error_message = "lambda_package_s3_bucket, lambda_package_s3_key and lambda_package_source_hash must be provided together."
    }
  }
}

resource "aws_lambda_function" "latest_projection" {
  function_name    = local.projection_lambda_name
  filename         = local.lambda_uses_s3_package ? null : data.archive_file.aws_serving_api[0].output_path
  s3_bucket        = local.lambda_uses_s3_package ? var.lambda_package_s3_bucket : null
  s3_key           = local.lambda_uses_s3_package ? var.lambda_package_s3_key : null
  source_code_hash = local.lambda_uses_s3_package ? var.lambda_package_source_hash : data.archive_file.aws_serving_api[0].output_base64sha256
  handler          = "projection_handler.lambda_handler"
  runtime          = var.lambda_runtime
  role             = aws_iam_role.latest_projection.arn
  timeout          = var.projection_lambda_timeout_seconds
  memory_size      = var.lambda_memory_mb

  environment {
    variables = merge(
      local.lambda_environment,
      {
        CACHE_TTL_DAYS         = tostring(var.cache_ttl_days)
        PROJECTION_QUERY_LIMIT = "1000"
      },
    )
  }

  depends_on = [
    aws_cloudwatch_log_group.projection_lambda,
    aws_iam_role_policy_attachment.latest_projection,
  ]

  lifecycle {
    precondition {
      condition     = length(local.lambda_package_s3_inputs) == 0 || local.lambda_uses_s3_package
      error_message = "lambda_package_s3_bucket, lambda_package_s3_key and lambda_package_source_hash must be provided together."
    }
  }
}
