output "kinesis_stream_name" {
  description = "Kinesis stream receiving canonical market candle JSON records."
  value       = aws_kinesis_stream.market_candles.name
}

output "kinesis_stream_arn" {
  description = "Kinesis stream ARN."
  value       = aws_kinesis_stream.market_candles.arn
}

output "ecr_repository_url" {
  description = "ECR repository URL for the Binance producer image."
  value       = aws_ecr_repository.binance_producer.repository_url
}

output "ecs_cluster_name" {
  description = "ECS cluster running the producer service."
  value       = aws_ecs_cluster.producer.name
}

output "ecs_service_name" {
  description = "ECS Fargate service name for the Binance producer."
  value       = aws_ecs_service.producer.name
}

output "ecs_task_role_name" {
  description = "IAM role used by the producer container."
  value       = aws_iam_role.ecs_task.name
}

output "ecs_task_execution_role_name" {
  description = "IAM role used by ECS to pull the image and write logs."
  value       = aws_iam_role.ecs_task_execution.name
}

output "producer_cloudwatch_log_group_name" {
  description = "CloudWatch log group used by the producer task."
  value       = aws_cloudwatch_log_group.producer.name
}
