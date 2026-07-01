locals {
  api_routes = toset([
    "GET /health",
    "GET /metrics/latest",
    "GET /metrics/history",
    "GET /signals",
    "GET /daily-summary",
  ])
}

resource "aws_apigatewayv2_api" "market" {
  name          = local.api_gateway_name
  protocol_type = "HTTP"

  cors_configuration {
    allow_headers = ["authorization", "content-type"]
    allow_methods = ["GET", "OPTIONS"]
    allow_origins = var.api_cors_allowed_origins
    max_age       = 300
  }
}

resource "aws_apigatewayv2_authorizer" "cognito" {
  api_id           = aws_apigatewayv2_api.market.id
  authorizer_type  = "JWT"
  identity_sources = ["$request.header.Authorization"]
  name             = "${local.name_prefix}-cognito-jwt"

  jwt_configuration {
    audience = [aws_cognito_user_pool_client.streamlit.id]
    issuer   = "https://${aws_cognito_user_pool.users.endpoint}"
  }
}

resource "aws_apigatewayv2_integration" "api_lambda" {
  api_id                 = aws_apigatewayv2_api.market.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.api.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "api" {
  for_each = local.api_routes

  api_id             = aws_apigatewayv2_api.market.id
  route_key          = each.value
  target             = "integrations/${aws_apigatewayv2_integration.api_lambda.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.market.id
  name        = local.api_stage_name
  auto_deploy = true

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api_gateway.arn
    format = jsonencode({
      requestId      = "$context.requestId"
      routeKey       = "$context.routeKey"
      status         = "$context.status"
      responseLength = "$context.responseLength"
      integrationMs  = "$context.integrationLatency"
    })
  }
}

resource "aws_lambda_permission" "api_gateway" {
  statement_id  = "AllowApiGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.api.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.market.execution_arn}/*/*"
}

resource "aws_cloudwatch_event_rule" "projection_refresh" {
  count = var.projection_schedule_enabled ? 1 : 0

  name                = "${local.name_prefix}-latest-projection-refresh"
  description         = "Refresh the DynamoDB latest metrics projection from trading_gold.market_indicators_latest."
  schedule_expression = var.projection_schedule_expression
}

resource "aws_cloudwatch_event_target" "projection_refresh" {
  count = var.projection_schedule_enabled ? 1 : 0

  rule      = aws_cloudwatch_event_rule.projection_refresh[0].name
  target_id = "latest-metrics-projection"
  arn       = aws_lambda_function.latest_projection.arn
}

resource "aws_lambda_permission" "projection_refresh" {
  count = var.projection_schedule_enabled ? 1 : 0

  statement_id  = "AllowEventBridgeProjectionRefresh"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.latest_projection.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.projection_refresh[0].arn
}
