variable "aws_region" {
  description = "AWS region used for the serving/API stack."
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

variable "lake_bucket_name" {
  description = "S3 lake bucket created by infra/aws/batch."
  type        = string
}

variable "athena_results_bucket_name" {
  description = "S3 bucket used by the Athena workgroup for query results."
  type        = string
}

variable "athena_results_prefix" {
  description = "S3 prefix used by Athena query results."
  type        = string
  default     = "athena-results"
}

variable "athena_output_location" {
  description = "S3 output location configured on the Athena workgroup."
  type        = string
}

variable "athena_workgroup_name" {
  description = "Athena workgroup name created by infra/aws/batch."
  type        = string
}

variable "trading_gold_database_name" {
  description = "Glue database that exposes trading_gold restitution tables."
  type        = string
  default     = "trading_gold"
}

variable "latest_metrics_table_name" {
  description = "Optional explicit DynamoDB table name for latest metrics."
  type        = string
  default     = null
}

variable "latest_metrics_ttl_enabled" {
  description = "Enable DynamoDB TTL on expires_at_epoch."
  type        = bool
  default     = true
}

variable "cache_ttl_days" {
  description = "TTL horizon in days written by the latest metrics projection."
  type        = number
  default     = 7
}

variable "allowed_symbols" {
  description = "Symbols accepted by the API."
  type        = list(string)
  default     = ["BTCUSDC", "ETHUSDC", "SOLUSDC"]
}

variable "allowed_intervals" {
  description = "Intervals accepted by the API."
  type        = list(string)
  default     = ["1s", "1m", "15m", "1h"]
}

variable "history_default_limit" {
  description = "Default item limit for Athena-backed API list endpoints."
  type        = number
  default     = 100
}

variable "history_max_limit" {
  description = "Maximum item limit for Athena-backed API list endpoints."
  type        = number
  default     = 500
}

variable "lambda_runtime" {
  description = "Python runtime used by the API and projection Lambda functions."
  type        = string
  default     = "python3.11"
}

variable "api_lambda_timeout_seconds" {
  description = "Timeout for the read-only API Lambda."
  type        = number
  default     = 30
}

variable "projection_lambda_timeout_seconds" {
  description = "Timeout for the latest metrics projection Lambda."
  type        = number
  default     = 60
}

variable "lambda_memory_mb" {
  description = "Memory for the API and projection Lambda functions."
  type        = number
  default     = 256
}

variable "lambda_package_s3_bucket" {
  description = "Optional S3 bucket containing the CI-published Lambda zip package. Leave null for local archive_file packaging."
  type        = string
  default     = null
}

variable "lambda_package_s3_key" {
  description = "Optional S3 key for the CI-published Lambda zip package. Leave null for local archive_file packaging."
  type        = string
  default     = null
}

variable "lambda_package_source_hash" {
  description = "Optional base64-encoded SHA-256 hash for the CI-published Lambda zip package."
  type        = string
  default     = null
}

variable "cloudwatch_log_retention_days" {
  description = "Retention period for serving/API CloudWatch logs."
  type        = number
  default     = 14
}

variable "projection_schedule_enabled" {
  description = "Enable the EventBridge refresh schedule for the DynamoDB latest projection."
  type        = bool
  default     = false
}

variable "projection_schedule_expression" {
  description = "EventBridge schedule expression used when projection_schedule_enabled is true."
  type        = string
  default     = "rate(15 minutes)"
}

variable "cognito_domain_prefix" {
  description = "Optional Cognito Hosted UI domain prefix. Must be globally unique."
  type        = string
  default     = null
}

variable "streamlit_callback_urls" {
  description = "Allowed Cognito callback URLs for Streamlit Cloud and local development."
  type        = list(string)
  default     = ["http://localhost:8501"]

  validation {
    condition     = length(var.streamlit_callback_urls) > 0
    error_message = "streamlit_callback_urls must contain at least one URL."
  }
}

variable "streamlit_logout_urls" {
  description = "Allowed Cognito logout URLs for Streamlit Cloud and local development."
  type        = list(string)
  default     = ["http://localhost:8501"]

  validation {
    condition     = length(var.streamlit_logout_urls) > 0
    error_message = "streamlit_logout_urls must contain at least one URL."
  }
}

variable "api_cors_allowed_origins" {
  description = "CORS origins allowed to call the API Gateway HTTP API."
  type        = list(string)
  default     = ["http://localhost:8501"]
}

variable "alert_email" {
  description = "Optional email address subscribed to POC alarms and Budget notifications."
  type        = string
  default     = null
}

variable "poc_budget_limit_eur" {
  description = "Monthly AWS Budget limit for the controlled POC."
  type        = number
  default     = 50
}

variable "budget_warning_thresholds" {
  description = "Budget warning thresholds expressed as percentages."
  type        = list(number)
  default     = [50, 80, 100]
}

variable "market_candles_stream_name" {
  description = "Kinesis market candle stream name used for alarms."
  type        = string
  default     = null
}

variable "ecs_cluster_name" {
  description = "ECS cluster name used for producer service alarms."
  type        = string
  default     = null
}

variable "ecs_service_name" {
  description = "ECS service name used for producer service alarms."
  type        = string
  default     = null
}

variable "glue_job_names" {
  description = "Glue job names used for log/observability references."
  type        = list(string)
  default     = []
}
