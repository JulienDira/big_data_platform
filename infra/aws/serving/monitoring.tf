locals {
  alarm_actions = var.alert_email == null ? [] : [aws_sns_topic.alerts[0].arn]
}

resource "aws_sns_topic" "alerts" {
  count = var.alert_email == null ? 0 : 1

  name = "${local.name_prefix}-poc-alerts"
}

resource "aws_sns_topic_subscription" "alerts_email" {
  count = var.alert_email == null ? 0 : 1

  topic_arn = aws_sns_topic.alerts[0].arn
  protocol  = "email"
  endpoint  = var.alert_email
}

resource "aws_cloudwatch_metric_alarm" "api_gateway_5xx" {
  alarm_name          = "${local.name_prefix}-api-gateway-5xx"
  alarm_description   = "API Gateway 5xx responses on the market data API."
  namespace           = "AWS/ApiGateway"
  metric_name         = "5xx"
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = local.alarm_actions

  dimensions = {
    ApiId = aws_apigatewayv2_api.market.id
    Stage = aws_apigatewayv2_stage.default.name
  }
}

resource "aws_cloudwatch_metric_alarm" "api_gateway_latency" {
  alarm_name          = "${local.name_prefix}-api-gateway-latency"
  alarm_description   = "Average API Gateway latency above the POC threshold."
  namespace           = "AWS/ApiGateway"
  metric_name         = "Latency"
  statistic           = "Average"
  period              = 300
  evaluation_periods  = 2
  threshold           = 3000
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = local.alarm_actions

  dimensions = {
    ApiId = aws_apigatewayv2_api.market.id
    Stage = aws_apigatewayv2_stage.default.name
  }
}

resource "aws_cloudwatch_metric_alarm" "api_lambda_errors" {
  alarm_name          = "${local.name_prefix}-api-lambda-errors"
  alarm_description   = "API Lambda errors."
  namespace           = "AWS/Lambda"
  metric_name         = "Errors"
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = local.alarm_actions

  dimensions = {
    FunctionName = aws_lambda_function.api.function_name
  }
}

resource "aws_cloudwatch_metric_alarm" "projection_lambda_errors" {
  alarm_name          = "${local.name_prefix}-latest-projection-errors"
  alarm_description   = "Latest metrics projection Lambda errors."
  namespace           = "AWS/Lambda"
  metric_name         = "Errors"
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = local.alarm_actions

  dimensions = {
    FunctionName = aws_lambda_function.latest_projection.function_name
  }
}

resource "aws_cloudwatch_metric_alarm" "dynamodb_read_throttles" {
  alarm_name          = "${local.name_prefix}-latest-dynamodb-read-throttles"
  alarm_description   = "DynamoDB latest metrics read throttles."
  namespace           = "AWS/DynamoDB"
  metric_name         = "ReadThrottleEvents"
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = local.alarm_actions

  dimensions = {
    TableName = aws_dynamodb_table.latest_metrics.name
  }
}

resource "aws_cloudwatch_metric_alarm" "dynamodb_write_throttles" {
  alarm_name          = "${local.name_prefix}-latest-dynamodb-write-throttles"
  alarm_description   = "DynamoDB latest metrics write throttles."
  namespace           = "AWS/DynamoDB"
  metric_name         = "WriteThrottleEvents"
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = local.alarm_actions

  dimensions = {
    TableName = aws_dynamodb_table.latest_metrics.name
  }
}

resource "aws_cloudwatch_metric_alarm" "kinesis_write_throttles" {
  alarm_name          = "${local.name_prefix}-kinesis-write-throttles"
  alarm_description   = "Kinesis write throttles on the market candles stream."
  namespace           = "AWS/Kinesis"
  metric_name         = "WriteProvisionedThroughputExceeded"
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = local.alarm_actions

  dimensions = {
    StreamName = local.market_candles_stream_name
  }
}

resource "aws_cloudwatch_metric_alarm" "kinesis_iterator_age" {
  alarm_name          = "${local.name_prefix}-kinesis-iterator-age"
  alarm_description   = "Kinesis iterator age above the controlled POC threshold."
  namespace           = "AWS/Kinesis"
  metric_name         = "GetRecords.IteratorAgeMilliseconds"
  statistic           = "Maximum"
  period              = 300
  evaluation_periods  = 2
  threshold           = 300000
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = local.alarm_actions

  dimensions = {
    StreamName = local.market_candles_stream_name
  }
}

resource "aws_cloudwatch_metric_alarm" "ecs_cpu_high" {
  alarm_name          = "${local.name_prefix}-producer-ecs-cpu-high"
  alarm_description   = "Producer ECS service CPU above the POC threshold."
  namespace           = "AWS/ECS"
  metric_name         = "CPUUtilization"
  statistic           = "Average"
  period              = 300
  evaluation_periods  = 2
  threshold           = 80
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = local.alarm_actions

  dimensions = {
    ClusterName = local.ecs_cluster_name
    ServiceName = local.ecs_service_name
  }
}

resource "aws_cloudwatch_event_rule" "glue_job_failures" {
  name        = "${local.name_prefix}-glue-job-failures"
  description = "Detect failed, timed out or stopped Glue jobs in the market pipeline."

  event_pattern = jsonencode({
    source        = ["aws.glue"]
    "detail-type" = ["Glue Job State Change"]
    detail = {
      jobName = local.effective_glue_job_names
      state   = ["FAILED", "TIMEOUT", "STOPPED"]
    }
  })
}

resource "aws_cloudwatch_event_target" "glue_job_failure_alerts" {
  count = var.alert_email == null ? 0 : 1

  rule      = aws_cloudwatch_event_rule.glue_job_failures.name
  target_id = "sns-alerts"
  arn       = aws_sns_topic.alerts[0].arn
}

resource "aws_budgets_budget" "poc" {
  name         = "${local.name_prefix}-poc-50-eur"
  budget_type  = "COST"
  limit_amount = tostring(var.poc_budget_limit_eur)
  limit_unit   = "EUR"
  time_unit    = "MONTHLY"

  dynamic "notification" {
    for_each = var.alert_email == null ? [] : var.budget_warning_thresholds

    content {
      comparison_operator        = "GREATER_THAN"
      threshold                  = notification.value
      threshold_type             = "PERCENTAGE"
      notification_type          = "ACTUAL"
      subscriber_email_addresses = [var.alert_email]
    }
  }
}
