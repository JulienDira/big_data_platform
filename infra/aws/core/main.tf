data "aws_caller_identity" "current" {}

data "aws_partition" "current" {}

data "aws_region" "current" {}

locals {
  project_slug = lower(replace(var.project_name, "_", "-"))
  env_slug     = lower(replace(var.environment, "_", "-"))
  name_prefix  = "${local.project_slug}-${local.env_slug}"

  kinesis_stream_name     = coalesce(var.kinesis_stream_name, "${local.name_prefix}-market-candles")
  ecr_repository_name     = coalesce(var.ecr_repository_name, "${local.name_prefix}-binance-producer")
  ecs_cluster_name        = coalesce(var.ecs_cluster_name, "${local.name_prefix}-producer")
  producer_service_name   = "${local.name_prefix}-binance-producer"
  producer_container_name = "binance-producer"
  producer_log_group_name = "/ecs/${local.producer_service_name}"
  producer_image          = "${aws_ecr_repository.binance_producer.repository_url}:${var.producer_image_tag}"
  producer_security_group = "${local.name_prefix}-producer-sg"
  producer_environment_vars = {
    AWS_REGION                 = var.aws_region
    BINANCE_BASE_URL           = var.binance_base_url
    KINESIS_PUBLISH_BATCH_SIZE = tostring(var.kinesis_publish_batch_size)
    KINESIS_STREAM_NAME        = aws_kinesis_stream.market_candles.name
    LOG_LEVEL                  = var.producer_log_level
    MARKET_INTERVALS           = join(",", var.market_intervals)
    MARKET_SYMBOLS             = join(",", var.market_symbols)
    PRODUCER_POLL_SECONDS      = tostring(var.producer_poll_seconds)
  }
}

resource "aws_kinesis_stream" "market_candles" {
  name             = local.kinesis_stream_name
  retention_period = var.kinesis_retention_hours
  shard_count      = var.kinesis_stream_mode == "PROVISIONED" ? var.kinesis_shard_count : null
  encryption_type  = "KMS"
  kms_key_id       = "alias/aws/kinesis"

  stream_mode_details {
    stream_mode = var.kinesis_stream_mode
  }
}

resource "aws_ecr_repository" "binance_producer" {
  name                 = local.ecr_repository_name
  force_delete         = var.ecr_force_delete
  image_tag_mutability = "IMMUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "AES256"
  }
}

resource "aws_cloudwatch_log_group" "producer" {
  name              = local.producer_log_group_name
  retention_in_days = var.cloudwatch_log_retention_days
}

resource "aws_ecs_cluster" "producer" {
  name = local.ecs_cluster_name
}

resource "aws_security_group" "producer" {
  name        = local.producer_security_group
  description = "Outbound-only security group for the Binance producer Fargate task."
  vpc_id      = var.vpc_id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = var.allowed_egress_cidr_blocks
  }
}

resource "aws_ecs_task_definition" "producer" {
  family                   = local.producer_service_name
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = tostring(var.producer_task_cpu)
  memory                   = tostring(var.producer_task_memory)
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name      = local.producer_container_name
      image     = local.producer_image
      essential = true
      command   = ["python", "/workspace/apps/binance-producer/aws.py"]
      environment = [
        for name, value in local.producer_environment_vars : {
          name  = name
          value = value
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.producer.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "producer"
        }
      }
    }
  ])
}

resource "aws_ecs_service" "producer" {
  name            = local.producer_service_name
  cluster         = aws_ecs_cluster.producer.id
  task_definition = aws_ecs_task_definition.producer.arn
  desired_count   = var.ecs_service_desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.fargate_subnet_ids
    security_groups  = [aws_security_group.producer.id]
    assign_public_ip = var.assign_public_ip
  }

  depends_on = [
    aws_cloudwatch_log_group.producer,
    aws_iam_role_policy_attachment.ecs_task_execution,
    aws_iam_role_policy_attachment.ecs_task,
  ]
}
