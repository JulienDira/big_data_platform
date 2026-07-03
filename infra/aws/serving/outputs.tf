output "latest_metrics_table_name" {
  description = "DynamoDB table used as the latest metrics cache."
  value       = aws_dynamodb_table.latest_metrics.name
}

output "api_gateway_endpoint" {
  description = "Base URL for the API Gateway HTTP API."
  value       = aws_apigatewayv2_stage.default.invoke_url
}

output "api_lambda_name" {
  description = "Read-only market API Lambda function name."
  value       = aws_lambda_function.api.function_name
}

output "latest_projection_lambda_name" {
  description = "DynamoDB latest projection Lambda function name."
  value       = aws_lambda_function.latest_projection.function_name
}

output "latest_projection_lambda_arn" {
  description = "DynamoDB latest projection Lambda function ARN."
  value       = aws_lambda_function.latest_projection.arn
}

output "cognito_user_pool_id" {
  description = "Cognito User Pool id."
  value       = aws_cognito_user_pool.users.id
}

output "cognito_streamlit_client_id" {
  description = "Public Cognito app client id for Streamlit."
  value       = aws_cognito_user_pool_client.streamlit.id
}

output "cognito_hosted_ui_domain" {
  description = "Cognito Hosted UI base domain for Streamlit OAuth."
  value       = "https://${aws_cognito_user_pool_domain.hosted_ui.domain}.auth.${var.aws_region}.amazoncognito.com"
}

output "cloudwatch_alarm_names" {
  description = "Minimal POC alarm names created by this stack."
  value = [
    aws_cloudwatch_metric_alarm.api_gateway_5xx.alarm_name,
    aws_cloudwatch_metric_alarm.api_gateway_latency.alarm_name,
    aws_cloudwatch_metric_alarm.api_lambda_errors.alarm_name,
    aws_cloudwatch_metric_alarm.projection_lambda_errors.alarm_name,
    aws_cloudwatch_metric_alarm.dynamodb_read_throttles.alarm_name,
    aws_cloudwatch_metric_alarm.dynamodb_write_throttles.alarm_name,
    aws_cloudwatch_metric_alarm.kinesis_write_throttles.alarm_name,
    aws_cloudwatch_metric_alarm.kinesis_iterator_age.alarm_name,
    aws_cloudwatch_metric_alarm.ecs_cpu_high.alarm_name,
  ]
}

output "poc_budget_name" {
  description = "AWS Budget name for the controlled POC."
  value       = aws_budgets_budget.poc.name
}
