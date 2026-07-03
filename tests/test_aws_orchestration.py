import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ORCHESTRATION = ROOT / "infra/aws/orchestration"
WORKFLOW = ROOT / ".github/workflows/aws-deploy.yml"


class AwsOrchestrationTest(unittest.TestCase):
    def setUp(self):
        self.main_source = (ORCHESTRATION / "main.tf").read_text(encoding="utf-8")
        self.iam_source = (ORCHESTRATION / "iam.tf").read_text(encoding="utf-8")
        self.variables_source = (ORCHESTRATION / "variables.tf").read_text(
            encoding="utf-8"
        )
        self.workflow_source = WORKFLOW.read_text(encoding="utf-8")

    def test_state_machine_runs_batch_jobs_in_order_then_projection(self):
        self.assertIn('resource "aws_sfn_state_machine" "batch_pipeline"', self.main_source)
        self.assertIn('QueryLanguage = "JSONata"', self.main_source)
        self.assertNotIn("ResultPath", self.main_source)
        self.assertNotIn("RunBronze", self.main_source)
        self.assertNotIn("var.bronze_glue_job_name", self.main_source)

        silver_index = self.main_source.index("RunSilver")
        gold_index = self.main_source.index("RunGold")
        projection_index = self.main_source.index("RunLatestProjection")

        self.assertLess(silver_index, gold_index)
        self.assertLess(gold_index, projection_index)

        self.assertIn("glue:startJobRun.sync", self.main_source)
        self.assertIn("JobName = var.silver_glue_job_name", self.main_source)
        self.assertIn("JobName = var.gold_glue_job_name", self.main_source)
        self.assertIn("lambda:invoke", self.main_source)
        self.assertIn("FunctionName = var.latest_projection_lambda_arn", self.main_source)

    def test_scheduler_is_every_minute_and_disabled_by_default(self):
        self.assertIn('resource "aws_scheduler_schedule" "batch_pipeline"', self.main_source)
        self.assertIn('default     = "rate(1 minute)"', self.variables_source)
        self.assertIn("default     = false", self.variables_source)
        self.assertIn(
            'state       = var.batch_pipeline_schedule_enabled ? "ENABLED" : "DISABLED"',
            self.main_source,
        )
        self.assertIn("schedule_expression = var.batch_pipeline_schedule_expression", self.main_source)
        self.assertIn('mode = "OFF"', self.main_source)

    def test_dynamodb_lock_uses_condition_and_ttl(self):
        self.assertIn('resource "aws_dynamodb_table" "pipeline_lock"', self.main_source)
        self.assertIn('hash_key     = "lock_name"', self.main_source)
        self.assertIn('attribute_name = "expires_at_epoch"', self.main_source)
        self.assertIn("enabled        = true", self.main_source)
        self.assertIn(
            "attribute_not_exists(lock_name) OR expires_at_epoch < :now_epoch",
            self.main_source,
        )
        self.assertIn("$millis()", self.main_source)
        self.assertIn("var.lock_ttl_seconds", self.main_source)
        self.assertIn("dynamodb:PutItem", self.iam_source)
        self.assertIn("dynamodb:DeleteItem", self.iam_source)

    def test_orchestration_exports_expected_outputs(self):
        outputs = (ORCHESTRATION / "outputs.tf").read_text(encoding="utf-8")
        self.assertIn('output "batch_pipeline_state_machine_arn"', outputs)
        self.assertIn('output "batch_pipeline_schedule_name"', outputs)
        self.assertIn('output "batch_pipeline_schedule_enabled"', outputs)
        self.assertIn('output "batch_pipeline_lock_table_name"', outputs)

        serving_outputs = (ROOT / "infra/aws/serving/outputs.tf").read_text(
            encoding="utf-8"
        )
        batch_outputs = (ROOT / "infra/aws/batch/outputs.tf").read_text(
            encoding="utf-8"
        )
        self.assertIn('output "latest_projection_lambda_arn"', serving_outputs)
        self.assertIn('output "bronze_glue_job_name"', batch_outputs)
        self.assertIn("bronze_streaming", batch_outputs)
        self.assertIn('output "silver_glue_job_name"', batch_outputs)
        self.assertIn('output "gold_glue_job_name"', batch_outputs)

    def test_workflow_validates_and_applies_orchestration_after_serving(self):
        self.assertIn("for stack in core batch serving orchestration; do", self.workflow_source)
        self.assertIn("Apply orchestration stack with schedule disabled", self.workflow_source)
        self.assertIn("-chdir=infra/aws/orchestration", self.workflow_source)
        self.assertIn('-var="batch_pipeline_schedule_enabled=false"', self.workflow_source)
        self.assertIn("latest_projection_lambda_arn", self.workflow_source)
        self.assertNotIn("bronze_glue_job_name=${{ steps.batch.outputs", self.workflow_source)

        serving_index = self.workflow_source.index(
            "Apply serving stack from immutable Lambda package"
        )
        orchestration_index = self.workflow_source.index(
            "Apply orchestration stack with schedule disabled"
        )
        self.assertLess(serving_index, orchestration_index)


if __name__ == "__main__":
    unittest.main()
