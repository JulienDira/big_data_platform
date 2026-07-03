data "aws_iam_policy_document" "state_machine_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["states.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "state_machine" {
  name               = "${local.name_prefix}-batch-pipeline-sfn-role"
  assume_role_policy = data.aws_iam_policy_document.state_machine_assume_role.json
}

data "aws_iam_policy_document" "state_machine" {
  statement {
    sid = "ManagePipelineLock"
    actions = [
      "dynamodb:DeleteItem",
      "dynamodb:PutItem",
    ]
    resources = [aws_dynamodb_table.pipeline_lock.arn]
  }

  statement {
    sid = "RunGlueBatchJobs"
    actions = [
      "glue:BatchStopJobRun",
      "glue:GetJobRun",
      "glue:GetJobRuns",
      "glue:StartJobRun",
    ]
    resources = ["*"]
  }

  statement {
    sid       = "InvokeLatestProjection"
    actions   = ["lambda:InvokeFunction"]
    resources = [var.latest_projection_lambda_arn]
  }

  statement {
    sid = "WriteStateMachineLogs"
    actions = [
      "logs:CreateLogDelivery",
      "logs:DeleteLogDelivery",
      "logs:DescribeLogGroups",
      "logs:DescribeResourcePolicies",
      "logs:GetLogDelivery",
      "logs:ListLogDeliveries",
      "logs:PutResourcePolicy",
      "logs:UpdateLogDelivery",
    ]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "state_machine" {
  name   = "${local.name_prefix}-batch-pipeline-sfn-policy"
  role   = aws_iam_role.state_machine.id
  policy = data.aws_iam_policy_document.state_machine.json
}

data "aws_iam_policy_document" "scheduler_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["scheduler.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "scheduler" {
  name               = "${local.name_prefix}-batch-pipeline-scheduler-role"
  assume_role_policy = data.aws_iam_policy_document.scheduler_assume_role.json
}

data "aws_iam_policy_document" "scheduler" {
  statement {
    sid       = "StartBatchPipelineStateMachine"
    actions   = ["states:StartExecution"]
    resources = [aws_sfn_state_machine.batch_pipeline.arn]
  }
}

resource "aws_iam_role_policy" "scheduler" {
  name   = "${local.name_prefix}-batch-pipeline-scheduler-policy"
  role   = aws_iam_role.scheduler.id
  policy = data.aws_iam_policy_document.scheduler.json
}
