output "lake_bucket_name" {
  description = "S3 bucket for Silver, Gold and trading_gold datasets."
  value       = aws_s3_bucket.lake.bucket
}

output "athena_results_bucket_name" {
  description = "S3 bucket used for Athena query results."
  value       = aws_s3_bucket.athena_results.bucket
}

output "raw_output_path" {
  description = "S3 path where the Raw Glue Streaming job writes Kinesis Avro envelopes."
  value       = local.raw_output_path
}

output "bronze_output_path" {
  description = "S3 path where the Bronze Glue job writes decoded market candles."
  value       = local.bronze_output_path
}

output "silver_input_path" {
  description = "S3 path expected by jobs/gold-indicators/aws.py for Silver input."
  value       = local.silver_input_path
}

output "bronze_rejected_output_path" {
  description = "S3 path where the Bronze Glue job writes rejected records."
  value       = local.bronze_rejected_output_path
}

output "raw_checkpoint_path" {
  description = "S3 path used by the Raw Glue Streaming checkpoint."
  value       = local.raw_checkpoint_path
}

output "gold_output_path" {
  description = "S3 path where the Glue job writes analytical Gold indicators."
  value       = local.gold_output_path
}

output "trading_gold_output_base_path" {
  description = "S3 base path where the Glue job writes trading_gold restitution datasets."
  value       = local.trading_gold_output_base_path
}

output "glue_databases" {
  description = "Glue Data Catalog database names."
  value       = local.glue_databases
}

output "glue_job_name" {
  description = "Glue Spark batch job name."
  value       = aws_glue_job.gold_indicators_batch.name
}

output "bronze_glue_job_name" {
  description = "Glue Streaming job name for Raw S3 to Bronze S3."
  value       = aws_glue_job.bronze_market_candles_streaming.name
}

output "silver_glue_job_name" {
  description = "Glue Spark batch job name for Bronze S3 to Silver S3."
  value       = aws_glue_job.silver_market_candles_batch.name
}

output "gold_glue_job_name" {
  description = "Glue Spark batch job name for Silver S3 to Gold and trading_gold S3."
  value       = aws_glue_job.gold_indicators_batch.name
}

output "lake_ingestion_glue_job_names" {
  description = "Glue job names for Raw, Bronze and Silver lake ingestion."
  value = {
    raw_streaming    = aws_glue_job.raw_market_candles_streaming.name
    bronze_streaming = aws_glue_job.bronze_market_candles_streaming.name
    silver_batch     = aws_glue_job.silver_market_candles_batch.name
  }
}

output "glue_artifact_key_prefix" {
  description = "S3 key prefix used for the Glue script, Python zips and SQL files."
  value       = local.glue_artifact_key_prefix
}

output "glue_artifact_bucket_name" {
  description = "S3 bucket containing the Glue script, Python zips and SQL files."
  value       = local.glue_artifact_bucket_name
}

output "glue_cloudwatch_log_group_name" {
  description = "CloudWatch log group used by the Glue Spark batch job."
  value       = aws_cloudwatch_log_group.glue_jobs.name
}

output "athena_workgroup_name" {
  description = "Athena workgroup configured for batch validation queries."
  value       = aws_athena_workgroup.batch.name
}

output "athena_output_location" {
  description = "S3 location used for Athena query results."
  value       = local.athena_output_location
}
