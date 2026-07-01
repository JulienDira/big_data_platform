variable "aws_region" {
  description = "AWS region used for the minimal batch stack."
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
  description = "Optional explicit S3 bucket name for Silver, Gold and trading_gold datasets."
  type        = string
  default     = null
}

variable "athena_results_bucket_name" {
  description = "Optional explicit S3 bucket name for Athena query results."
  type        = string
  default     = null
}

variable "force_destroy_buckets" {
  description = "Allow Terraform to delete non-empty S3 buckets. Keep false outside disposable environments."
  type        = bool
  default     = false
}

variable "silver_dataset_prefix" {
  description = "S3 prefix for the Silver market candles dataset."
  type        = string
  default     = "silver/market_candles"
}

variable "gold_dataset_prefix" {
  description = "S3 prefix for the analytical Gold market indicators dataset."
  type        = string
  default     = "gold/market_indicators"
}

variable "trading_gold_dataset_prefix" {
  description = "S3 base prefix for AWS restitution datasets exposed as trading_gold tables."
  type        = string
  default     = "trading_gold"
}

variable "glue_artifacts_prefix" {
  description = "S3 prefix where Terraform uploads the Glue script and Python/SQL artifacts."
  type        = string
  default     = "artifacts/glue/gold-indicators"
}

variable "glue_artifact_version" {
  description = "Version segment used below glue_artifacts_prefix for scripts, Python zips and SQL artifacts."
  type        = string
  default     = "local-dev"
}

variable "athena_output_prefix" {
  description = "S3 prefix for Athena query results."
  type        = string
  default     = "athena-results"
}

variable "silver_database_name" {
  description = "Glue database name for Silver datasets."
  type        = string
  default     = "silver"
}

variable "gold_database_name" {
  description = "Glue database name for analytical Gold datasets."
  type        = string
  default     = "gold"
}

variable "trading_gold_database_name" {
  description = "Glue database name for AWS restitution datasets."
  type        = string
  default     = "trading_gold"
}

variable "partition_projection_symbols" {
  description = "Symbols exposed through Athena partition projection."
  type        = list(string)
  default     = ["BTCUSDC", "ETHUSDC", "SOLUSDC"]
}

variable "partition_projection_intervals" {
  description = "Intervals exposed through Athena partition projection."
  type        = list(string)
  default     = ["1s", "1m", "15m", "1h"]
}

variable "partition_projection_date_range" {
  description = "Athena partition projection range for event_date partitions."
  type        = string
  default     = "2025-01-01,NOW"
}

variable "glue_version" {
  description = "AWS Glue version for the Spark batch job."
  type        = string
  default     = "4.0"
}

variable "glue_worker_type" {
  description = "Glue worker type for the Spark batch job."
  type        = string
  default     = "G.1X"
}

variable "glue_number_of_workers" {
  description = "Number of Glue workers for the Spark batch job."
  type        = number
  default     = 2
}

variable "glue_job_timeout_minutes" {
  description = "Timeout for the Glue batch job."
  type        = number
  default     = 60
}

variable "glue_job_max_retries" {
  description = "Maximum retries for the Glue batch job."
  type        = number
  default     = 0
}

variable "cloudwatch_log_retention_days" {
  description = "Retention period for Glue CloudWatch logs."
  type        = number
  default     = 14
}

variable "datamart_base_interval" {
  description = "Base interval used by the AWS restitution transformations."
  type        = string
  default     = "1m"
}

variable "datamart_context_intervals" {
  description = "Two context intervals used by the AWS restitution transformations."
  type        = list(string)
  default     = ["15m", "1h"]

  validation {
    condition     = length(var.datamart_context_intervals) == 2
    error_message = "datamart_context_intervals must contain exactly two values."
  }
}
