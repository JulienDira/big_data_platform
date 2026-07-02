data "aws_iam_policy_document" "lambda_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "api_lambda" {
  name               = "${local.name_prefix}-api-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
}

resource "aws_iam_role" "latest_projection" {
  name               = "${local.name_prefix}-latest-projection-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
}

data "aws_iam_policy_document" "api_lambda" {
  statement {
    sid = "ReadLatestMetricsCache"
    actions = [
      "dynamodb:DescribeTable",
      "dynamodb:GetItem",
      "dynamodb:Query",
    ]
    resources = [aws_dynamodb_table.latest_metrics.arn]
  }

  statement {
    sid = "RunBoundedAthenaQueries"
    actions = [
      "athena:GetQueryExecution",
      "athena:GetQueryResults",
      "athena:StartQueryExecution",
      "athena:StopQueryExecution",
    ]
    resources = [
      "arn:${data.aws_partition.current.partition}:athena:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:workgroup/${var.athena_workgroup_name}",
    ]
  }

  statement {
    sid = "ReadTradingGoldCatalog"
    actions = [
      "glue:GetDatabase",
      "glue:GetDatabases",
      "glue:GetPartition",
      "glue:GetPartitions",
      "glue:GetTable",
      "glue:GetTables",
    ]
    resources = [
      "arn:${data.aws_partition.current.partition}:glue:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:catalog",
      "arn:${data.aws_partition.current.partition}:glue:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:database/${var.trading_gold_database_name}",
      "arn:${data.aws_partition.current.partition}:glue:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:table/${var.trading_gold_database_name}/*",
    ]
  }

  statement {
    sid = "UseAthenaResultLocationOnly"
    actions = [
      "s3:GetBucketLocation",
      "s3:ListBucket",
    ]
    resources = [local.athena_results_bucket_arn]

    condition {
      test     = "StringLike"
      variable = "s3:prefix"
      values = [
        local.athena_results_prefix,
        "${local.athena_results_prefix}/*",
      ]
    }
  }

  statement {
    sid = "ReadWriteAthenaResultsOnly"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
    ]
    resources = [
      "${local.athena_results_bucket_arn}/${local.athena_results_prefix}/*",
    ]
  }

  statement {
    sid = "WriteApiLogs"
    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]
    resources = ["${aws_cloudwatch_log_group.api_lambda.arn}:*"]
  }
}

resource "aws_iam_policy" "api_lambda" {
  name        = "${local.name_prefix}-api-lambda-policy"
  description = "Read-only market API access to DynamoDB latest metrics and Athena trading_gold tables."
  policy      = data.aws_iam_policy_document.api_lambda.json
}

resource "aws_iam_role_policy_attachment" "api_lambda" {
  role       = aws_iam_role.api_lambda.name
  policy_arn = aws_iam_policy.api_lambda.arn
}

data "aws_iam_policy_document" "latest_projection" {
  statement {
    sid = "WriteLatestMetricsCache"
    actions = [
      "dynamodb:DescribeTable",
      "dynamodb:PutItem",
    ]
    resources = [aws_dynamodb_table.latest_metrics.arn]
  }

  statement {
    sid = "ReadLatestTradingGoldViaAthena"
    actions = [
      "athena:GetQueryExecution",
      "athena:GetQueryResults",
      "athena:StartQueryExecution",
      "athena:StopQueryExecution",
    ]
    resources = [
      "arn:${data.aws_partition.current.partition}:athena:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:workgroup/${var.athena_workgroup_name}",
    ]
  }

  statement {
    sid = "ReadTradingGoldLatestCatalog"
    actions = [
      "glue:GetDatabase",
      "glue:GetDatabases",
      "glue:GetPartition",
      "glue:GetPartitions",
      "glue:GetTable",
      "glue:GetTables",
    ]
    resources = [
      "arn:${data.aws_partition.current.partition}:glue:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:catalog",
      "arn:${data.aws_partition.current.partition}:glue:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:database/${var.trading_gold_database_name}",
      "arn:${data.aws_partition.current.partition}:glue:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:table/${var.trading_gold_database_name}/market_indicators_latest",
    ]
  }

  statement {
    sid = "UseProjectionAthenaResultLocationOnly"
    actions = [
      "s3:GetBucketLocation",
      "s3:ListBucket",
    ]
    resources = [local.athena_results_bucket_arn]

    condition {
      test     = "StringLike"
      variable = "s3:prefix"
      values = [
        local.athena_results_prefix,
        "${local.athena_results_prefix}/*",
      ]
    }
  }

  statement {
    sid = "ReadWriteProjectionAthenaResultsOnly"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
    ]
    resources = [
      "${local.athena_results_bucket_arn}/${local.athena_results_prefix}/*",
    ]
  }

  statement {
    sid = "WriteProjectionLogs"
    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]
    resources = ["${aws_cloudwatch_log_group.projection_lambda.arn}:*"]
  }
}

resource "aws_iam_policy" "latest_projection" {
  name        = "${local.name_prefix}-latest-projection-policy"
  description = "Read trading_gold latest metrics through Athena and write the DynamoDB latest cache."
  policy      = data.aws_iam_policy_document.latest_projection.json
}

resource "aws_iam_role_policy_attachment" "latest_projection" {
  role       = aws_iam_role.latest_projection.name
  policy_arn = aws_iam_policy.latest_projection.arn
}
