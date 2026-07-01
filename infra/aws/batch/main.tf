data "aws_caller_identity" "current" {}

data "aws_partition" "current" {}

data "aws_region" "current" {}

locals {
  repo_root    = abspath("${path.module}/../../..")
  project_slug = lower(replace(var.project_name, "_", "-"))
  env_slug     = lower(replace(var.environment, "_", "-"))
  name_prefix  = "${local.project_slug}-${local.env_slug}"

  default_bucket_prefix       = "${local.name_prefix}-${data.aws_caller_identity.current.account_id}-${data.aws_region.current.name}"
  lake_bucket_name            = coalesce(var.lake_bucket_name, "${local.default_bucket_prefix}-lake")
  athena_results_bucket_name  = coalesce(var.athena_results_bucket_name, "${local.default_bucket_prefix}-athena")
  silver_dataset_prefix       = trim(var.silver_dataset_prefix, "/")
  gold_dataset_prefix         = trim(var.gold_dataset_prefix, "/")
  trading_gold_dataset_prefix = trim(var.trading_gold_dataset_prefix, "/")
  glue_artifacts_prefix       = trim(var.glue_artifacts_prefix, "/")
  glue_artifact_version       = trim(var.glue_artifact_version, "/")
  glue_artifact_key_prefix    = local.glue_artifact_version == "" ? local.glue_artifacts_prefix : "${local.glue_artifacts_prefix}/${local.glue_artifact_version}"
  athena_output_prefix        = trim(var.athena_output_prefix, "/")

  silver_input_path             = "s3://${aws_s3_bucket.lake.bucket}/${local.silver_dataset_prefix}"
  gold_output_path              = "s3://${aws_s3_bucket.lake.bucket}/${local.gold_dataset_prefix}"
  trading_gold_output_base_path = "s3://${aws_s3_bucket.lake.bucket}/${local.trading_gold_dataset_prefix}"
  athena_output_location        = "s3://${aws_s3_bucket.athena_results.bucket}/${local.athena_output_prefix}/"
  glue_spark_event_logs_path    = "s3://${aws_s3_bucket.lake.bucket}/${local.glue_artifacts_prefix}/spark-event-logs"
  glue_temp_path                = "s3://${aws_s3_bucket.lake.bucket}/${local.glue_artifacts_prefix}/tmp"
  glue_script_key               = "${local.glue_artifact_key_prefix}/jobs/gold-indicators/aws.py"
  jobs_utils_key                = "${local.glue_artifact_key_prefix}/python/jobs-utils.zip"
  serving_registry_key          = "${local.glue_artifact_key_prefix}/python/serving-registry.zip"
  glue_script_s3_uri            = "s3://${aws_s3_bucket.lake.bucket}/${local.glue_script_key}"
  jobs_utils_s3_uri             = "s3://${aws_s3_bucket.lake.bucket}/${local.jobs_utils_key}"
  serving_registry_s3_uri       = "s3://${aws_s3_bucket.lake.bucket}/${local.serving_registry_key}"
  glue_job_name                 = "${local.name_prefix}-gold-indicators-batch"
  glue_log_group_name           = "/aws-glue/jobs/${local.glue_job_name}"
  athena_workgroup_name         = "${local.name_prefix}-batch"
  sql_files = toset([
    "market_daily_summary.sql",
    "market_indicators.sql",
    "market_indicators_latest.sql",
    "market_multitimeframe_signals.sql",
  ])
  sql_file_s3_uris = [
    for file_name in sort(tolist(local.sql_files)) :
    "s3://${aws_s3_bucket.lake.bucket}/${local.glue_artifact_key_prefix}/sql/${file_name}"
  ]
}

resource "aws_s3_bucket" "lake" {
  bucket        = local.lake_bucket_name
  force_destroy = var.force_destroy_buckets
}

resource "aws_s3_bucket_public_access_block" "lake" {
  bucket = aws_s3_bucket.lake.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "lake" {
  bucket = aws_s3_bucket.lake.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_versioning" "lake" {
  bucket = aws_s3_bucket.lake.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "lake" {
  bucket = aws_s3_bucket.lake.id

  rule {
    id     = "abort-incomplete-multipart-uploads"
    status = "Enabled"

    filter {
      prefix = ""
    }

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

resource "aws_s3_bucket" "athena_results" {
  bucket        = local.athena_results_bucket_name
  force_destroy = var.force_destroy_buckets
}

resource "aws_s3_bucket_public_access_block" "athena_results" {
  bucket = aws_s3_bucket.athena_results.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "athena_results" {
  bucket = aws_s3_bucket.athena_results.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "athena_results" {
  bucket = aws_s3_bucket.athena_results.id

  rule {
    id     = "abort-incomplete-multipart-uploads"
    status = "Enabled"

    filter {
      prefix = ""
    }

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

data "archive_file" "jobs_utils" {
  type        = "zip"
  source_dir  = "${local.repo_root}/jobs/utils"
  output_path = "${path.module}/.terraform/jobs-utils.zip"
}

data "archive_file" "serving_registry" {
  type        = "zip"
  output_path = "${path.module}/.terraform/serving-registry.zip"

  source {
    content  = file("${local.repo_root}/jobs/serving-datamart/registry.py")
    filename = "registry.py"
  }
}

resource "aws_s3_object" "glue_script" {
  bucket       = aws_s3_bucket.lake.id
  key          = local.glue_script_key
  source       = "${local.repo_root}/jobs/gold-indicators/aws.py"
  etag         = filemd5("${local.repo_root}/jobs/gold-indicators/aws.py")
  content_type = "text/x-python"
}

resource "aws_s3_object" "jobs_utils" {
  bucket      = aws_s3_bucket.lake.id
  key         = local.jobs_utils_key
  source      = data.archive_file.jobs_utils.output_path
  source_hash = data.archive_file.jobs_utils.output_base64sha256
}

resource "aws_s3_object" "serving_registry" {
  bucket      = aws_s3_bucket.lake.id
  key         = local.serving_registry_key
  source      = data.archive_file.serving_registry.output_path
  source_hash = data.archive_file.serving_registry.output_base64sha256
}

resource "aws_s3_object" "serving_sql" {
  for_each = local.sql_files

  bucket       = aws_s3_bucket.lake.id
  key          = "${local.glue_artifact_key_prefix}/sql/${each.value}"
  source       = "${local.repo_root}/jobs/serving-datamart/sql/${each.value}"
  etag         = filemd5("${local.repo_root}/jobs/serving-datamart/sql/${each.value}")
  content_type = "text/plain"
}

resource "aws_cloudwatch_log_group" "glue_jobs" {
  name              = local.glue_log_group_name
  retention_in_days = var.cloudwatch_log_retention_days
}

resource "aws_athena_workgroup" "batch" {
  name = local.athena_workgroup_name

  configuration {
    enforce_workgroup_configuration = true

    result_configuration {
      output_location = local.athena_output_location

      encryption_configuration {
        encryption_option = "SSE_S3"
      }
    }
  }
}
