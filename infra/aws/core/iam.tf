data "aws_iam_policy_document" "ecs_tasks_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "ecs_task" {
  name               = "${local.name_prefix}-producer-task-role"
  assume_role_policy = data.aws_iam_policy_document.ecs_tasks_assume_role.json
}

data "aws_iam_policy_document" "ecs_task" {
  statement {
    sid = "WriteMarketCandlesStream"
    actions = [
      "kinesis:PutRecord",
      "kinesis:PutRecords",
    ]
    resources = [
      aws_kinesis_stream.market_candles.arn,
    ]
  }
}

resource "aws_iam_policy" "ecs_task" {
  name        = "${local.name_prefix}-producer-task-policy"
  description = "Allow the Binance producer task to publish market candles to Kinesis."
  policy      = data.aws_iam_policy_document.ecs_task.json
}

resource "aws_iam_role_policy_attachment" "ecs_task" {
  role       = aws_iam_role.ecs_task.name
  policy_arn = aws_iam_policy.ecs_task.arn
}

resource "aws_iam_role" "ecs_task_execution" {
  name               = "${local.name_prefix}-producer-execution-role"
  assume_role_policy = data.aws_iam_policy_document.ecs_tasks_assume_role.json
}

data "aws_iam_policy_document" "ecs_task_execution" {
  statement {
    sid = "EcrAuthorization"
    actions = [
      "ecr:GetAuthorizationToken",
    ]
    resources = ["*"]
  }

  statement {
    sid = "PullProducerImage"
    actions = [
      "ecr:BatchCheckLayerAvailability",
      "ecr:BatchGetImage",
      "ecr:GetDownloadUrlForLayer",
    ]
    resources = [
      aws_ecr_repository.binance_producer.arn,
    ]
  }

  statement {
    sid = "WriteProducerLogs"
    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]
    resources = [
      "${aws_cloudwatch_log_group.producer.arn}:*",
    ]
  }
}

resource "aws_iam_policy" "ecs_task_execution" {
  name        = "${local.name_prefix}-producer-execution-policy"
  description = "Allow ECS to pull the producer image and write producer logs."
  policy      = data.aws_iam_policy_document.ecs_task_execution.json
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution" {
  role       = aws_iam_role.ecs_task_execution.name
  policy_arn = aws_iam_policy.ecs_task_execution.arn
}

resource "aws_iam_service_linked_role" "ecs" {
  aws_service_name = "ecs.amazonaws.com"
}
