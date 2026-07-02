import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/aws-deploy.yml"


class AwsDeployWorkflowTest(unittest.TestCase):
    def setUp(self):
        self.source = WORKFLOW.read_text(encoding="utf-8")

    def test_workflow_uses_oidc_and_github_environment(self):
        self.assertIn("id-token: write", self.source)
        self.assertIn("aws-actions/configure-aws-credentials@v6.1.0", self.source)
        self.assertIn("role-to-assume: ${{ vars.AWS_DEPLOY_ROLE_ARN }}", self.source)
        self.assertIn("aws-region: ${{ vars.AWS_REGION }}", self.source)
        self.assertIn("environment: dev", self.source)

    def test_pull_requests_validate_without_publication_or_apply(self):
        self.assertIn("pull_request:", self.source)
        self.assertIn("push:", self.source)
        self.assertIn("branches: [main]", self.source)
        self.assertIn("workflow_dispatch:", self.source)
        self.assertIn("if: github.event_name != 'pull_request'", self.source)

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

    def test_workflow_does_not_run_runtime_aws_services(self):
        forbidden = (
            "start-job-run",
            "update-service --desired-count",
            "put-record",
            "put-records",
            "streamlit deploy",
        )
        for token in forbidden:
            self.assertNotIn(token, self.source)


if __name__ == "__main__":
    unittest.main()
