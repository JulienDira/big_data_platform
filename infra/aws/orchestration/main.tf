data "aws_caller_identity" "current" {}

data "aws_partition" "current" {}

data "aws_region" "current" {}

locals {
  project_slug = lower(replace(var.project_name, "_", "-"))
  env_slug     = lower(replace(var.environment, "_", "-"))
  name_prefix  = "${local.project_slug}-${local.env_slug}"

  lock_name          = "batch-pipeline"
  lock_table_name    = "${local.name_prefix}-batch-pipeline-lock"
  log_group_name     = "/aws/vendedlogs/states/${local.name_prefix}-batch-pipeline"
  schedule_name      = "${local.name_prefix}-batch-pipeline-every-minute"
  state_machine_name = "${local.name_prefix}-batch-pipeline"
}

resource "aws_dynamodb_table" "pipeline_lock" {
  name         = local.lock_table_name
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "lock_name"

  attribute {
    name = "lock_name"
    type = "S"
  }

  ttl {
    attribute_name = "expires_at_epoch"
    enabled        = true
  }

  server_side_encryption {
    enabled = true
  }
}

resource "aws_cloudwatch_log_group" "state_machine" {
  name              = local.log_group_name
  retention_in_days = var.cloudwatch_log_retention_days
}

resource "aws_sfn_state_machine" "batch_pipeline" {
  name     = local.state_machine_name
  role_arn = aws_iam_role.state_machine.arn
  type     = "STANDARD"

  logging_configuration {
    include_execution_data = true
    level                  = "ALL"
    log_destination        = "${aws_cloudwatch_log_group.state_machine.arn}:*"
  }

  definition = jsonencode({
    QueryLanguage = "JSONata"
    Comment       = "Run Silver, Gold and latest projection in order with a DynamoDB single-flight lock."
    StartAt       = "AcquireLock"
    States = {
      AcquireLock = {
        Type     = "Task"
        Resource = "arn:${data.aws_partition.current.partition}:states:::dynamodb:putItem"
        Arguments = {
          TableName = aws_dynamodb_table.pipeline_lock.name
          Item = {
            lock_name = {
              S = local.lock_name
            }
            owner_execution_arn = {
              S = "{% $states.context.Execution.Id %}"
            }
            acquired_at = {
              S = "{% $now() %}"
            }
            expires_at_epoch = {
              N = "{% $string($floor($millis() / 1000) + ${var.lock_ttl_seconds}) %}"
            }
          }
          ConditionExpression = "attribute_not_exists(lock_name) OR expires_at_epoch < :now_epoch"
          ExpressionAttributeValues = {
            ":now_epoch" = {
              N = "{% $string($floor($millis() / 1000)) %}"
            }
          }
        }
        Next = "RunSilver"
        Catch = [
          {
            ErrorEquals = ["DynamoDB.ConditionalCheckFailedException"]
            Next        = "AlreadyRunning"
          },
          {
            ErrorEquals = ["States.ALL"]
            Next        = "WorkflowFailed"
          },
        ]
      }
      AlreadyRunning = {
        Type = "Succeed"
      }
      RunSilver = {
        Type     = "Task"
        Resource = "arn:${data.aws_partition.current.partition}:states:::glue:startJobRun.sync"
        Arguments = {
          JobName = var.silver_glue_job_name
        }
        Next = "RunGold"
        Catch = [
          {
            ErrorEquals = ["States.ALL"]
            Next        = "ReleaseLockAfterFailure"
          },
        ]
      }
      RunGold = {
        Type     = "Task"
        Resource = "arn:${data.aws_partition.current.partition}:states:::glue:startJobRun.sync"
        Arguments = {
          JobName = var.gold_glue_job_name
        }
        Next = "RunLatestProjection"
        Catch = [
          {
            ErrorEquals = ["States.ALL"]
            Next        = "ReleaseLockAfterFailure"
          },
        ]
      }
      RunLatestProjection = {
        Type     = "Task"
        Resource = "arn:${data.aws_partition.current.partition}:states:::lambda:invoke"
        Arguments = {
          FunctionName = var.latest_projection_lambda_arn
          Payload = {
            source = "step-functions-batch-pipeline"
          }
        }
        Next = "ReleaseLockAfterSuccess"
        Catch = [
          {
            ErrorEquals = ["States.ALL"]
            Next        = "ReleaseLockAfterFailure"
          },
        ]
      }
      ReleaseLockAfterSuccess = {
        Type     = "Task"
        Resource = "arn:${data.aws_partition.current.partition}:states:::dynamodb:deleteItem"
        Arguments = {
          TableName = aws_dynamodb_table.pipeline_lock.name
          Key = {
            lock_name = {
              S = local.lock_name
            }
          }
          ConditionExpression = "owner_execution_arn = :owner_execution_arn"
          ExpressionAttributeValues = {
            ":owner_execution_arn" = {
              S = "{% $states.context.Execution.Id %}"
            }
          }
        }
        Next = "WorkflowSucceeded"
        Catch = [
          {
            ErrorEquals = ["States.ALL"]
            Next        = "WorkflowSucceeded"
          },
        ]
      }
      ReleaseLockAfterFailure = {
        Type     = "Task"
        Resource = "arn:${data.aws_partition.current.partition}:states:::dynamodb:deleteItem"
        Arguments = {
          TableName = aws_dynamodb_table.pipeline_lock.name
          Key = {
            lock_name = {
              S = local.lock_name
            }
          }
          ConditionExpression = "owner_execution_arn = :owner_execution_arn"
          ExpressionAttributeValues = {
            ":owner_execution_arn" = {
              S = "{% $states.context.Execution.Id %}"
            }
          }
        }
        Next = "WorkflowFailed"
        Catch = [
          {
            ErrorEquals = ["States.ALL"]
            Next        = "WorkflowFailed"
          },
        ]
      }
      WorkflowSucceeded = {
        Type = "Succeed"
      }
      WorkflowFailed = {
        Type  = "Fail"
        Error = "BatchPipelineFailed"
        Cause = "One of the scheduled batch pipeline steps failed."
      }
    }
  })

  depends_on = [
    aws_cloudwatch_log_group.state_machine,
    aws_iam_role_policy.state_machine,
  ]
}

resource "aws_scheduler_schedule" "batch_pipeline" {
  name        = local.schedule_name
  description = "Triggers the AWS batch pipeline orchestration every minute when enabled."
  state       = var.batch_pipeline_schedule_enabled ? "ENABLED" : "DISABLED"

  flexible_time_window {
    mode = "OFF"
  }

  schedule_expression = var.batch_pipeline_schedule_expression

  target {
    arn      = aws_sfn_state_machine.batch_pipeline.arn
    role_arn = aws_iam_role.scheduler.arn
    input = jsonencode({
      source   = "eventbridge-scheduler"
      pipeline = local.lock_name
    })
  }

  depends_on = [
    aws_iam_role_policy.scheduler,
  ]
}
