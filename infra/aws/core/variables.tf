variable "aws_region" {
  description = "AWS region used for the core producer stack."
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

variable "vpc_id" {
  description = "VPC where the Fargate producer service runs."
  type        = string
}

variable "fargate_subnet_ids" {
  description = "Subnets used by the Fargate producer service."
  type        = list(string)

  validation {
    condition     = length(var.fargate_subnet_ids) > 0
    error_message = "fargate_subnet_ids must contain at least one subnet id."
  }
}

variable "assign_public_ip" {
  description = "Assign a public IP to the Fargate task. Useful for low-cost public-subnet POCs without NAT."
  type        = bool
  default     = true
}

variable "allowed_egress_cidr_blocks" {
  description = "CIDR blocks allowed for producer outbound traffic."
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "kinesis_stream_name" {
  description = "Optional explicit Kinesis stream name for market candles."
  type        = string
  default     = null
}

variable "kinesis_stream_mode" {
  description = "Kinesis stream mode: PROVISIONED or ON_DEMAND."
  type        = string
  default     = "PROVISIONED"

  validation {
    condition     = contains(["PROVISIONED", "ON_DEMAND"], var.kinesis_stream_mode)
    error_message = "kinesis_stream_mode must be PROVISIONED or ON_DEMAND."
  }
}

variable "kinesis_shard_count" {
  description = "Shard count used when kinesis_stream_mode is PROVISIONED."
  type        = number
  default     = 1

  validation {
    condition     = var.kinesis_shard_count >= 1
    error_message = "kinesis_shard_count must be at least 1."
  }
}

variable "kinesis_retention_hours" {
  description = "Kinesis retention period in hours."
  type        = number
  default     = 24
}

variable "kinesis_publish_batch_size" {
  description = "Producer PutRecords batch size."
  type        = number
  default     = 500

  validation {
    condition     = var.kinesis_publish_batch_size >= 1 && var.kinesis_publish_batch_size <= 500
    error_message = "kinesis_publish_batch_size must be between 1 and 500."
  }
}

variable "ecr_repository_name" {
  description = "Optional explicit ECR repository name for the Binance producer image."
  type        = string
  default     = null
}

variable "ecr_force_delete" {
  description = "Allow Terraform to delete the ECR repository even when it contains images."
  type        = bool
  default     = false
}

variable "producer_image_tag" {
  description = "Image tag already pushed to ECR for the ECS task definition."
  type        = string
  default     = "manual"
}

variable "ecs_cluster_name" {
  description = "Optional explicit ECS cluster name."
  type        = string
  default     = null
}

variable "ecs_service_desired_count" {
  description = "Number of Binance producer tasks."
  type        = number
  default     = 1
}

variable "producer_task_cpu" {
  description = "Fargate task CPU units."
  type        = number
  default     = 256
}

variable "producer_task_memory" {
  description = "Fargate task memory in MiB."
  type        = number
  default     = 512
}

variable "market_symbols" {
  description = "Symbols handled by the first AWS producer task."
  type        = list(string)
  default     = ["BTCUSDC", "ETHUSDC", "SOLUSDC"]

  validation {
    condition     = length(var.market_symbols) > 0
    error_message = "market_symbols must contain at least one symbol."
  }
}

variable "market_intervals" {
  description = "Intervals handled by the first AWS producer task."
  type        = list(string)
  default     = ["1s", "1m", "15m", "1h"]

  validation {
    condition     = length(var.market_intervals) > 0
    error_message = "market_intervals must contain at least one interval."
  }
}

variable "binance_base_url" {
  description = "Binance REST base URL used by the AWS producer."
  type        = string
  default     = "https://api.binance.com"
}

variable "producer_poll_seconds" {
  description = "Producer polling delay in seconds."
  type        = number
  default     = 15
}

variable "producer_log_level" {
  description = "Python log level for the producer."
  type        = string
  default     = "INFO"
}

variable "cloudwatch_log_retention_days" {
  description = "Retention period for the producer CloudWatch log group."
  type        = number
  default     = 14
}
