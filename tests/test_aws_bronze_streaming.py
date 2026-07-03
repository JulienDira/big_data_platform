import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BRONZE_AWS = ROOT / "jobs/bronze-ingestion/aws.py"
BATCH = ROOT / "infra/aws/batch"


class AwsBronzeStreamingTest(unittest.TestCase):
    def setUp(self):
        self.bronze_source = BRONZE_AWS.read_text(encoding="utf-8")
        self.glue_job_source = (BATCH / "glue_job.tf").read_text(encoding="utf-8")
        self.variables_source = (BATCH / "variables.tf").read_text(encoding="utf-8")
        self.main_source = (BATCH / "main.tf").read_text(encoding="utf-8")
        self.outputs_source = (BATCH / "outputs.tf").read_text(encoding="utf-8")

    def test_bronze_aws_entrypoint_is_structured_streaming(self):
        self.assertIn("AWS_RAW_MARKET_CANDLES_SCHEMA", self.bronze_source)
        self.assertIn("spark.readStream.schema(AWS_RAW_MARKET_CANDLES_SCHEMA)", self.bronze_source)
        self.assertIn('.option("basePath", raw_input_path)', self.bronze_source)
        self.assertIn('.option("maxFilesPerTrigger", max_files_per_trigger)', self.bronze_source)
        self.assertIn("build_bronze_valid(decoded, watermark_delay=watermark_delay)", self.bronze_source)
        self.assertIn("write_parquet_stream(", self.bronze_source)
        self.assertIn("BRONZE_CHECKPOINT_PATH", self.bronze_source)
        self.assertIn("BRONZE_REJECTED_CHECKPOINT_PATH", self.bronze_source)
        self.assertNotIn("write_parquet_dataset", self.bronze_source)
        self.assertNotIn("WRITE_MODE", self.bronze_source)
        self.assertNotIn(".mode(", self.bronze_source)

    def test_bronze_glue_job_is_streaming_with_checkpoint_arguments(self):
        self.assertIn('resource "aws_glue_job" "bronze_market_candles_streaming"', self.glue_job_source)
        self.assertNotIn('resource "aws_glue_job" "bronze_market_candles_batch"', self.glue_job_source)

        bronze_resource = self.glue_job_source[
            self.glue_job_source.index('resource "aws_glue_job" "bronze_market_candles_streaming"') :
            self.glue_job_source.index('resource "aws_glue_job" "silver_market_candles_batch"')
        ]
        self.assertIn('name            = "gluestreaming"', bronze_resource)
        self.assertIn('"--BRONZE_CHECKPOINT_PATH"', bronze_resource)
        self.assertIn('"--BRONZE_REJECTED_CHECKPOINT_PATH"', bronze_resource)
        self.assertIn('"--BRONZE_TRIGGER_INTERVAL"', bronze_resource)
        self.assertIn('"--BRONZE_WATERMARK_DELAY"', bronze_resource)
        self.assertIn('"--BRONZE_MAX_FILES_PER_TRIGGER"', bronze_resource)
        self.assertNotIn('"--WRITE_MODE"', bronze_resource)

    def test_bronze_streaming_configuration_is_in_batch_source_of_truth(self):
        for variable_name in (
            'variable "bronze_checkpoint_prefix"',
            'variable "bronze_trigger_interval"',
            'variable "bronze_watermark_delay"',
            'variable "bronze_max_files_per_trigger"',
        ):
            self.assertIn(variable_name, self.variables_source)

        self.assertIn("bronze_checkpoint_path", self.main_source)
        self.assertIn("bronze_rejected_checkpoint_path", self.main_source)
        self.assertIn("bronze-market-candles-streaming", self.main_source)
        self.assertIn("bronze_streaming", self.outputs_source)

    def test_lake_transform_iam_includes_bronze_checkpoints_only_in_lake_scope(self):
        lake_policy = self.glue_job_source[
            self.glue_job_source.index('data "aws_iam_policy_document" "glue_lake_transform"') :
            self.glue_job_source.index('resource "aws_iam_policy" "glue_lake_transform"')
        ]
        self.assertIn("local.bronze_checkpoint_prefix", lake_policy)
        self.assertNotIn("local.gold_dataset_prefix", lake_policy)
        self.assertNotIn("local.trading_gold_dataset_prefix", lake_policy)
        self.assertNotIn("dynamodb:", lake_policy.lower())
        self.assertNotIn("lambda:", lake_policy.lower())


if __name__ == "__main__":
    unittest.main()
