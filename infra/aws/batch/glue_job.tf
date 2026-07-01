data "aws_iam_policy_document" "glue_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["glue.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "glue_batch" {
  name               = "${local.name_prefix}-glue-batch-role"
  assume_role_policy = data.aws_iam_policy_document.glue_assume_role.json
}

resource "aws_iam_role_policy_attachment" "glue_service_role" {
  role       = aws_iam_role.glue_batch.name
  policy_arn = "arn:${data.aws_partition.current.partition}:iam::aws:policy/service-role/AWSGlueServiceRole"
}

data "aws_iam_policy_document" "glue_batch" {
  statement {
    sid = "LakeBucketLocation"
    actions = [
      "s3:GetBucketLocation",
    ]
    resources = [
      aws_s3_bucket.lake.arn,
    ]
  }

  statement {
    sid = "LakeBatchPrefixList"
    actions = [
      "s3:ListBucket",
    ]
    resources = [
      aws_s3_bucket.lake.arn,
    ]

    condition {
      test     = "StringLike"
      variable = "s3:prefix"
      values = [
        local.silver_dataset_prefix,
        "${local.silver_dataset_prefix}/*",
        local.gold_dataset_prefix,
        "${local.gold_dataset_prefix}/*",
        local.trading_gold_dataset_prefix,
        "${local.trading_gold_dataset_prefix}/*",
        local.glue_artifacts_prefix,
        "${local.glue_artifacts_prefix}/*",
      ]
    }
  }

  statement {
    sid = "ReadSilverAndGlueArtifacts"
    actions = [
      "s3:GetObject",
    ]
    resources = [
      "${aws_s3_bucket.lake.arn}/${local.silver_dataset_prefix}/*",
      "${aws_s3_bucket.lake.arn}/${local.glue_artifacts_prefix}/*",
    ]
  }

  statement {
    sid = "WriteGoldTradingGoldAndRuntimeData"
    actions = [
      "s3:AbortMultipartUpload",
      "s3:DeleteObject",
      "s3:GetObject",
      "s3:ListMultipartUploadParts",
      "s3:PutObject",
    ]
    resources = [
      "${aws_s3_bucket.lake.arn}/${local.gold_dataset_prefix}/*",
      "${aws_s3_bucket.lake.arn}/${local.trading_gold_dataset_prefix}/*",
      "${aws_s3_bucket.lake.arn}/${local.glue_artifacts_prefix}/spark-event-logs/*",
      "${aws_s3_bucket.lake.arn}/${local.glue_artifacts_prefix}/tmp/*",
    ]
  }

  statement {
    sid = "GlueCatalogAccess"
    actions = [
      "glue:BatchCreatePartition",
      "glue:BatchDeletePartition",
      "glue:CreatePartition",
      "glue:GetDatabase",
      "glue:GetDatabases",
      "glue:GetPartition",
      "glue:GetPartitions",
      "glue:GetTable",
      "glue:GetTables",
      "glue:UpdatePartition",
    ]
    resources = concat(
      [
        "arn:${data.aws_partition.current.partition}:glue:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:catalog",
      ],
      [
        for database_name in values(local.glue_databases) :
        "arn:${data.aws_partition.current.partition}:glue:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:database/${database_name}"
      ],
      [
        for database_name in values(local.glue_databases) :
        "arn:${data.aws_partition.current.partition}:glue:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:table/${database_name}/*"
      ],
    )
  }

  statement {
    sid = "GlueCloudWatchLogs"
    actions = [
      "logs:CreateLogStream",
      "logs:DescribeLogGroups",
      "logs:DescribeLogStreams",
      "logs:PutLogEvents",
    ]
    resources = [
      "${aws_cloudwatch_log_group.glue_jobs.arn}:*",
    ]
  }
}

resource "aws_iam_policy" "glue_batch" {
  name        = "${local.name_prefix}-glue-batch-policy"
  description = "Minimal S3, Glue Catalog and CloudWatch access for the batch Gold Glue job."
  policy      = data.aws_iam_policy_document.glue_batch.json
}

resource "aws_iam_role_policy_attachment" "glue_batch" {
  role       = aws_iam_role.glue_batch.name
  policy_arn = aws_iam_policy.glue_batch.arn
}

resource "aws_glue_job" "gold_indicators_batch" {
  name         = local.glue_job_name
  role_arn     = aws_iam_role.glue_batch.arn
  glue_version = var.glue_version
  worker_type  = var.glue_worker_type

  number_of_workers = var.glue_number_of_workers
  timeout           = var.glue_job_timeout_minutes
  max_retries       = var.glue_job_max_retries

  command {
    name            = "glueetl"
    python_version  = "3"
    script_location = local.glue_script_s3_uri
  }

  default_arguments = {
    "--DATAMART_BASE_INTERVAL"           = var.datamart_base_interval
    "--DATAMART_CONTEXT_INTERVALS"       = join(",", var.datamart_context_intervals)
    "--GOLD_OUTPUT_PATH"                 = local.gold_output_path
    "--SILVER_INPUT_PATH"                = local.silver_input_path
    "--TRADING_GOLD_OUTPUT_BASE_PATH"    = local.trading_gold_output_base_path
    "--TempDir"                          = "${local.glue_temp_path}/"
    "--continuous-log-logGroup"          = aws_cloudwatch_log_group.glue_jobs.name
    "--continuous-log-logStreamPrefix"   = local.glue_job_name
    "--enable-continuous-cloudwatch-log" = "true"
    "--enable-glue-datacatalog"          = "true"
    "--enable-metrics"                   = "true"
    "--enable-spark-ui"                  = "true"
    "--extra-files"                      = join(",", local.sql_file_s3_uris)
    "--extra-py-files"                   = join(",", [local.jobs_utils_s3_uri, local.serving_registry_s3_uri])
    "--job-language"                     = "python"
    "--spark-event-logs-path"            = "${local.glue_spark_event_logs_path}/"
  }

  execution_property {
    max_concurrent_runs = 1
  }

  depends_on = [
    aws_iam_role_policy_attachment.glue_batch,
    aws_iam_role_policy_attachment.glue_service_role,
    aws_s3_object.glue_script,
    aws_s3_object.jobs_utils,
    aws_s3_object.serving_registry,
    aws_s3_object.serving_sql,
  ]
}
