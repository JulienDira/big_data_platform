data "aws_iam_policy_document" "glue_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["glue.amazonaws.com"]
    }
  }
}

data "aws_kinesis_stream" "market" {
  name = var.market_candles_stream_name
}

resource "aws_iam_role" "glue_batch" {
  name               = "${local.name_prefix}-glue-batch-role"
  assume_role_policy = data.aws_iam_policy_document.glue_assume_role.json
}

resource "aws_iam_role" "glue_raw_streaming" {
  name               = "${local.name_prefix}-glue-raw-streaming-role"
  assume_role_policy = data.aws_iam_policy_document.glue_assume_role.json
}

resource "aws_iam_role" "glue_lake_transform" {
  name               = "${local.name_prefix}-glue-lake-transform-role"
  assume_role_policy = data.aws_iam_policy_document.glue_assume_role.json
}

resource "aws_iam_role_policy_attachment" "glue_service_role" {
  role       = aws_iam_role.glue_batch.name
  policy_arn = "arn:${data.aws_partition.current.partition}:iam::aws:policy/service-role/AWSGlueServiceRole"
}

resource "aws_iam_role_policy_attachment" "glue_raw_streaming_service_role" {
  role       = aws_iam_role.glue_raw_streaming.name
  policy_arn = "arn:${data.aws_partition.current.partition}:iam::aws:policy/service-role/AWSGlueServiceRole"
}

resource "aws_iam_role_policy_attachment" "glue_lake_transform_service_role" {
  role       = aws_iam_role.glue_lake_transform.name
  policy_arn = "arn:${data.aws_partition.current.partition}:iam::aws:policy/service-role/AWSGlueServiceRole"
}

data "aws_iam_policy_document" "glue_raw_streaming" {
  statement {
    sid = "ReadMarketCandlesStream"
    actions = [
      "kinesis:DescribeStream",
      "kinesis:DescribeStreamSummary",
      "kinesis:GetRecords",
      "kinesis:GetShardIterator",
      "kinesis:ListShards",
      "kinesis:SubscribeToShard",
    ]
    resources = [
      data.aws_kinesis_stream.market.arn,
    ]
  }

  statement {
    sid = "LakeRawPrefixList"
    actions = [
      "s3:GetBucketLocation",
      "s3:ListBucket",
    ]
    resources = [
      aws_s3_bucket.lake.arn,
      local.glue_artifact_bucket_arn,
    ]

    condition {
      test     = "StringLike"
      variable = "s3:prefix"
      values = [
        local.raw_dataset_prefix,
        "${local.raw_dataset_prefix}/*",
        local.raw_checkpoint_prefix,
        "${local.raw_checkpoint_prefix}/*",
        local.glue_artifacts_prefix,
        "${local.glue_artifacts_prefix}/*",
      ]
    }
  }

  statement {
    sid = "ReadRawGlueArtifacts"
    actions = [
      "s3:GetObject",
    ]
    resources = [
      "${local.glue_artifact_bucket_arn}/${local.glue_artifacts_prefix}/*",
    ]
  }

  statement {
    sid = "WriteRawCheckpointAndRuntimeData"
    actions = [
      "s3:AbortMultipartUpload",
      "s3:DeleteObject",
      "s3:GetObject",
      "s3:ListMultipartUploadParts",
      "s3:PutObject",
    ]
    resources = [
      "${aws_s3_bucket.lake.arn}/${local.raw_dataset_prefix}/*",
      "${aws_s3_bucket.lake.arn}/${local.raw_checkpoint_prefix}/*",
      "${aws_s3_bucket.lake.arn}/${local.glue_artifacts_prefix}/spark-event-logs/*",
      "${aws_s3_bucket.lake.arn}/${local.glue_artifacts_prefix}/tmp/*",
    ]
  }

  statement {
    sid = "GlueRawCatalogAccess"
    actions = [
      "glue:BatchCreatePartition",
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
        "arn:${data.aws_partition.current.partition}:glue:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:database/${var.raw_database_name}",
        "arn:${data.aws_partition.current.partition}:glue:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:table/${var.raw_database_name}/*",
      ],
    )
  }

  statement {
    sid = "GlueRawCloudWatchLogs"
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

resource "aws_iam_policy" "glue_raw_streaming" {
  name        = "${local.name_prefix}-glue-raw-streaming-policy"
  description = "Minimal Kinesis, S3 and CloudWatch access for Raw Glue Streaming."
  policy      = data.aws_iam_policy_document.glue_raw_streaming.json
}

resource "aws_iam_role_policy_attachment" "glue_raw_streaming" {
  role       = aws_iam_role.glue_raw_streaming.name
  policy_arn = aws_iam_policy.glue_raw_streaming.arn
}

data "aws_iam_policy_document" "glue_lake_transform" {
  statement {
    sid = "LakeTransformPrefixList"
    actions = [
      "s3:GetBucketLocation",
      "s3:ListBucket",
    ]
    resources = [
      aws_s3_bucket.lake.arn,
      local.glue_artifact_bucket_arn,
    ]

    condition {
      test     = "StringLike"
      variable = "s3:prefix"
      values = [
        local.raw_dataset_prefix,
        "${local.raw_dataset_prefix}/*",
        local.bronze_dataset_prefix,
        "${local.bronze_dataset_prefix}/*",
        local.bronze_checkpoint_prefix,
        "${local.bronze_checkpoint_prefix}/*",
        local.bronze_rejected_prefix,
        "${local.bronze_rejected_prefix}/*",
        local.silver_dataset_prefix,
        "${local.silver_dataset_prefix}/*",
        local.glue_artifacts_prefix,
        "${local.glue_artifacts_prefix}/*",
      ]
    }
  }

  statement {
    sid = "ReadRawBronzeAndGlueArtifacts"
    actions = [
      "s3:GetObject",
    ]
    resources = [
      "${aws_s3_bucket.lake.arn}/${local.raw_dataset_prefix}/*",
      "${aws_s3_bucket.lake.arn}/${local.bronze_dataset_prefix}/*",
      "${local.glue_artifact_bucket_arn}/${local.glue_artifacts_prefix}/*",
    ]
  }

  statement {
    sid = "WriteBronzeSilverRejectedAndRuntimeData"
    actions = [
      "s3:AbortMultipartUpload",
      "s3:DeleteObject",
      "s3:GetObject",
      "s3:ListMultipartUploadParts",
      "s3:PutObject",
    ]
    resources = [
      "${aws_s3_bucket.lake.arn}/${local.bronze_dataset_prefix}/*",
      "${aws_s3_bucket.lake.arn}/${local.bronze_checkpoint_prefix}/*",
      "${aws_s3_bucket.lake.arn}/${local.bronze_rejected_prefix}/*",
      "${aws_s3_bucket.lake.arn}/${local.silver_dataset_prefix}/*",
      "${aws_s3_bucket.lake.arn}/${local.glue_artifacts_prefix}/spark-event-logs/*",
      "${aws_s3_bucket.lake.arn}/${local.glue_artifacts_prefix}/tmp/*",
    ]
  }

  statement {
    sid = "GlueLakeCatalogAccess"
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
        for database_name in [
          var.raw_database_name,
          var.bronze_database_name,
          var.silver_database_name,
        ] :
        "arn:${data.aws_partition.current.partition}:glue:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:database/${database_name}"
      ],
      [
        for database_name in [
          var.raw_database_name,
          var.bronze_database_name,
          var.silver_database_name,
        ] :
        "arn:${data.aws_partition.current.partition}:glue:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:table/${database_name}/*"
      ],
    )
  }

  statement {
    sid = "GlueLakeCloudWatchLogs"
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

resource "aws_iam_policy" "glue_lake_transform" {
  name        = "${local.name_prefix}-glue-lake-transform-policy"
  description = "Minimal S3, Glue Catalog and CloudWatch access for Bronze/Silver transforms."
  policy      = data.aws_iam_policy_document.glue_lake_transform.json
}

resource "aws_iam_role_policy_attachment" "glue_lake_transform" {
  role       = aws_iam_role.glue_lake_transform.name
  policy_arn = aws_iam_policy.glue_lake_transform.arn
}

data "aws_iam_policy_document" "glue_batch" {
  statement {
    sid = "LakeBucketLocation"
    actions = [
      "s3:GetBucketLocation",
    ]
    resources = [
      aws_s3_bucket.lake.arn,
      local.glue_artifact_bucket_arn,
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
      "${local.glue_artifact_bucket_arn}/${local.glue_artifacts_prefix}/*",
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

resource "aws_glue_job" "raw_market_candles_streaming" {
  name         = local.raw_glue_job_name
  role_arn     = aws_iam_role.glue_raw_streaming.arn
  glue_version = var.glue_version
  worker_type  = var.glue_worker_type

  number_of_workers = var.glue_number_of_workers
  timeout           = var.glue_job_timeout_minutes
  max_retries       = var.glue_job_max_retries

  command {
    name            = "gluestreaming"
    python_version  = "3"
    script_location = local.raw_script_s3_uri
  }

  default_arguments = {
    "--AWS_REGION"                       = var.aws_region
    "--CONTRACT_PATH"                    = "market-candle-v1.avsc"
    "--KINESIS_STARTING_POSITION"        = var.kinesis_starting_position
    "--KINESIS_STREAM_NAME"              = var.market_candles_stream_name
    "--RAW_CHECKPOINT_PATH"              = local.raw_checkpoint_path
    "--RAW_OUTPUT_PATH"                  = local.raw_output_path
    "--RAW_TRIGGER_INTERVAL"             = var.raw_trigger_interval
    "--TempDir"                          = "${local.glue_temp_path}/"
    "--continuous-log-logGroup"          = aws_cloudwatch_log_group.glue_jobs.name
    "--continuous-log-logStreamPrefix"   = local.raw_glue_job_name
    "--enable-continuous-cloudwatch-log" = "true"
    "--enable-glue-datacatalog"          = "true"
    "--enable-metrics"                   = "true"
    "--enable-spark-ui"                  = "true"
    "--extra-files"                      = local.contract_s3_uri
    "--extra-py-files"                   = local.jobs_utils_s3_uri
    "--job-language"                     = "python"
    "--spark-event-logs-path"            = "${local.glue_spark_event_logs_path}/"
  }

  execution_property {
    max_concurrent_runs = 1
  }

  depends_on = [
    aws_iam_role_policy_attachment.glue_raw_streaming,
    aws_iam_role_policy_attachment.glue_raw_streaming_service_role,
    aws_s3_object.raw_script,
    aws_s3_object.jobs_utils,
    aws_s3_object.market_candle_contract,
  ]
}

resource "aws_glue_job" "bronze_market_candles_streaming" {
  name         = local.bronze_glue_job_name
  role_arn     = aws_iam_role.glue_lake_transform.arn
  glue_version = var.glue_version
  worker_type  = var.glue_worker_type

  number_of_workers = var.glue_number_of_workers
  timeout           = var.glue_job_timeout_minutes
  max_retries       = var.glue_job_max_retries

  command {
    name            = "gluestreaming"
    python_version  = "3"
    script_location = local.bronze_script_s3_uri
  }

  default_arguments = {
    "--BRONZE_CHECKPOINT_PATH"           = local.bronze_checkpoint_path
    "--BRONZE_MAX_FILES_PER_TRIGGER"     = tostring(var.bronze_max_files_per_trigger)
    "--BRONZE_OUTPUT_PATH"               = local.bronze_output_path
    "--BRONZE_REJECTED_CHECKPOINT_PATH"  = local.bronze_rejected_checkpoint_path
    "--BRONZE_REJECTED_OUTPUT_PATH"      = local.bronze_rejected_output_path
    "--BRONZE_TRIGGER_INTERVAL"          = var.bronze_trigger_interval
    "--BRONZE_WATERMARK_DELAY"           = var.bronze_watermark_delay
    "--CONTRACT_PATH"                    = "market-candle-v1.avsc"
    "--RAW_INPUT_PATH"                   = local.raw_output_path
    "--TempDir"                          = "${local.glue_temp_path}/"
    "--continuous-log-logGroup"          = aws_cloudwatch_log_group.glue_jobs.name
    "--continuous-log-logStreamPrefix"   = local.bronze_glue_job_name
    "--enable-continuous-cloudwatch-log" = "true"
    "--enable-glue-datacatalog"          = "true"
    "--enable-metrics"                   = "true"
    "--enable-spark-ui"                  = "true"
    "--extra-files"                      = local.contract_s3_uri
    "--extra-py-files"                   = local.jobs_utils_s3_uri
    "--job-language"                     = "python"
    "--spark-event-logs-path"            = "${local.glue_spark_event_logs_path}/"
  }

  execution_property {
    max_concurrent_runs = 1
  }

  depends_on = [
    aws_iam_role_policy_attachment.glue_lake_transform,
    aws_iam_role_policy_attachment.glue_lake_transform_service_role,
    aws_s3_object.bronze_script,
    aws_s3_object.jobs_utils,
    aws_s3_object.market_candle_contract,
  ]
}

resource "aws_glue_job" "silver_market_candles_batch" {
  name         = local.silver_glue_job_name
  role_arn     = aws_iam_role.glue_lake_transform.arn
  glue_version = var.glue_version
  worker_type  = var.glue_worker_type

  number_of_workers = var.glue_number_of_workers
  timeout           = var.glue_job_timeout_minutes
  max_retries       = var.glue_job_max_retries

  command {
    name            = "glueetl"
    python_version  = "3"
    script_location = local.silver_script_s3_uri
  }

  default_arguments = {
    "--BRONZE_INPUT_PATH"                = local.bronze_output_path
    "--SILVER_OUTPUT_PATH"               = local.silver_input_path
    "--TempDir"                          = "${local.glue_temp_path}/"
    "--WRITE_MODE"                       = "overwrite"
    "--continuous-log-logGroup"          = aws_cloudwatch_log_group.glue_jobs.name
    "--continuous-log-logStreamPrefix"   = local.silver_glue_job_name
    "--enable-continuous-cloudwatch-log" = "true"
    "--enable-glue-datacatalog"          = "true"
    "--enable-metrics"                   = "true"
    "--enable-spark-ui"                  = "true"
    "--extra-py-files"                   = local.jobs_utils_s3_uri
    "--job-language"                     = "python"
    "--spark-event-logs-path"            = "${local.glue_spark_event_logs_path}/"
  }

  execution_property {
    max_concurrent_runs = 1
  }

  depends_on = [
    aws_iam_role_policy_attachment.glue_lake_transform,
    aws_iam_role_policy_attachment.glue_lake_transform_service_role,
    aws_s3_object.silver_script,
    aws_s3_object.jobs_utils,
  ]
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
