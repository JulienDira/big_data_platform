variable "aws_region" {
  description = "AWS region used for the batch orchestration stack."
  type        = string
  default     = "eu-west-3"
}

variable "project_name" {
  description = "Project name used in AWS resource names and tags."
  type        = string
  default     = "big-data-platform"
}

variable "environment" {
  description = "Environment name used in AWS resource names and tags."
  type        = string
  default     = "dev"
}

variable "tags" {
  description = "Additional tags applied to AWS resources."
  type        = map(string)
  default     = {}
}

variable "batch_pipeline_schedule_enabled" {
  description = "Enable the one-minute EventBridge Scheduler trigger for the batch pipeline."
  type        = bool
  default     = false
}

variable "batch_pipeline_schedule_expression" {
  description = "EventBridge Scheduler rate expression for the batch pipeline."
  type        = string
  default     = "rate(1 minute)"
}

variable "bronze_glue_job_name" {
  description = "Glue job name for Raw S3 to Bronze S3."
  type        = string
}

variable "silver_glue_job_name" {
  description = "Glue job name for Bronze S3 to Silver S3."
  type        = string
}

variable "gold_glue_job_name" {
  description = "Glue job name for Silver S3 to Gold and trading_gold S3."
  type        = string
}

variable "latest_projection_lambda_arn" {
  description = "ARN of the Lambda function that projects trading_gold latest metrics to DynamoDB."
  type        = string
}

variable "lock_ttl_seconds" {
  description = "Lease duration for the global batch-pipeline DynamoDB lock."
  type        = number
  default     = 3600

  validation {
    condition     = var.lock_ttl_seconds >= 300
    error_message = "lock_ttl_seconds must be at least 300 seconds."
  }
}

variable "cloudwatch_log_retention_days" {
  description = "Retention period for Step Functions CloudWatch logs."
  type        = number
  default     = 14
}
