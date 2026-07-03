output "batch_pipeline_state_machine_arn" {
  description = "ARN of the Step Functions state machine that orchestrates the scheduled AWS batch pipeline."
  value       = aws_sfn_state_machine.batch_pipeline.arn
}

output "batch_pipeline_schedule_name" {
  description = "EventBridge Scheduler schedule name for the AWS batch pipeline."
  value       = aws_scheduler_schedule.batch_pipeline.name
}

output "batch_pipeline_schedule_enabled" {
  description = "Whether the one-minute batch pipeline schedule is enabled."
  value       = var.batch_pipeline_schedule_enabled
}

output "batch_pipeline_lock_table_name" {
  description = "DynamoDB table name used for the global batch-pipeline lock."
  value       = aws_dynamodb_table.pipeline_lock.name
}

output "batch_pipeline_log_group_name" {
  description = "CloudWatch log group used by the Step Functions batch pipeline."
  value       = aws_cloudwatch_log_group.state_machine.name
}
