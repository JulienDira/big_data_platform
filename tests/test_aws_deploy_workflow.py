import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/aws-deploy.yml"
DESTROY_WORKFLOW = ROOT / ".github/workflows/aws-destroy.yml"


class AwsDeployWorkflowTest(unittest.TestCase):
    def setUp(self):
        self.source = WORKFLOW.read_text(encoding="utf-8")

    def test_workflow_uses_job_scoped_oidc_and_github_environment(self):
        self.assertRegex(
            self.source,
            r"permissions:\n  contents: read\n\nenv:",
            "Workflow-level permissions should not grant OIDC globally.",
        )
        self.assertEqual(3, self.source.count("id-token: write"))
        self.assertIn("aws-actions/configure-aws-credentials@", self.source)
        self.assertIn("role-to-assume: ${{ vars.AWS_DEPLOY_ROLE_ARN }}", self.source)
        self.assertIn("allowed-account-ids: ${{ vars.AWS_ACCOUNT_ID }}", self.source)
        self.assertIn("mask-aws-account-id: true", self.source)
        self.assertIn("unset-current-credentials: true", self.source)
        self.assertIn("environment: dev", self.source)

    def test_deployment_is_manual_only(self):
        self.assertNotIn("pull_request:", self.source)
        self.assertNotIn("push:", self.source)
        self.assertIn("workflow_dispatch:", self.source)
        self.assertEqual(3, self.source.count("if: github.event_name != 'pull_request'"))

    def test_actions_are_pinned_to_full_commit_sha_with_source_tag_comments(self):
        for comment in (
            "actions/checkout@v6.0.1",
            "actions/setup-python@v6.1.0",
            "aws-actions/configure-aws-credentials@v6.1.0",
            "hashicorp/setup-terraform@v3",
        ):
            self.assertIn(comment, self.source)

        uses_lines = re.findall(r"uses: ([^\n]+)", self.source)
        for value in uses_lines:
            action, ref = value.rsplit("@", 1)
            self.assertIn("/", action)
            self.assertRegex(ref, r"^[0-9a-f]{40}$", value)

    def test_workflow_avoids_long_lived_aws_keys(self):
        forbidden = (
            "AWS_ACCESS_KEY_ID",
            "AWS_SECRET_ACCESS_KEY",
            "aws-access-key-id",
            "aws-secret-access-key",
            "secrets.",
        )
        for token in forbidden:
            self.assertNotIn(token, self.source)

    def test_workflow_uses_s3_lockfile_backend(self):
        self.assertNotIn("TF_STATE_LOCK_TABLE", self.source)
        self.assertNotIn("dynamodb_table", self.source)
        self.assertIn('-backend-config="use_lockfile=true"', self.source)

    def test_runtime_commands_are_delegated_to_runtime_script_only(self):
        forbidden_in_workflow = (
            "start-job-run",
            "update-service --desired-count",
            "put-record",
            "put-records",
            "streamlit deploy",
        )
        for token in forbidden_in_workflow:
            self.assertNotIn(token, self.source)
        self.assertIn("python infra/scripts/aws-runtime-validate.py", self.source)

    def test_deployment_jobs_use_concurrency_without_canceling_running_apply(self):
        self.assertIn("group: aws-dev-deployment", self.source)
        self.assertIn("cancel-in-progress: false", self.source)

    def test_destroy_workflow_exists_with_manual_confirmation_and_reverse_order(self):
        self.assertTrue(DESTROY_WORKFLOW.exists(), "Destroy workflow should exist")
        source = DESTROY_WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("name: AWS Destroy", source)
        self.assertIn("workflow_dispatch:", source)
        self.assertIn("confirm_destroy:", source)
        self.assertIn("type: choice", source)
        self.assertIn("options:", source)
        self.assertIn("DESTROY", source)
        self.assertIn("concurrency:", source)
        self.assertIn("force_destroy_buckets=true", source)
        self.assertIn("Collect destroy inputs from existing stacks", source)
        self.assertIn("terraform -chdir=infra/aws/batch output -raw silver_glue_job_name", source)
        self.assertIn("terraform -chdir=infra/aws/batch output -raw gold_glue_job_name", source)
        self.assertIn("terraform -chdir=infra/aws/serving output -raw latest_projection_lambda_arn", source)
        self.assertIn("terraform -chdir=infra/aws/batch output -raw lake_bucket_name", source)
        self.assertIn("terraform -chdir=infra/aws/batch output -raw athena_results_bucket_name", source)
        self.assertIn("terraform -chdir=infra/aws/batch output -raw athena_output_location", source)
        self.assertIn("terraform -chdir=infra/aws/batch output -raw athena_workgroup_name", source)
        self.assertIn("terraform -chdir=infra/aws/core output -raw kinesis_stream_name", source)
        self.assertIn("terraform -chdir=infra/aws/core output -raw kinesis_stream_arn", source)
        self.assertIn("terraform -chdir=infra/aws/orchestration destroy", source)
        self.assertIn("terraform -chdir=infra/aws/serving destroy", source)
        self.assertIn("terraform -chdir=infra/aws/batch destroy", source)
        self.assertIn("terraform -chdir=infra/aws/core destroy", source)


if __name__ == "__main__":
    unittest.main()
