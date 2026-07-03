import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "infra/aws/README.md"


class AwsReadmeTest(unittest.TestCase):
    def setUp(self):
        self.source = README.read_text(encoding="utf-8")

    def test_readme_documents_required_official_references(self):
        urls = (
            "https://docs.github.com/en/actions/how-tos/secure-your-work/security-harden-deployments/oidc-in-aws",
            "https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments",
            "https://docs.github.com/en/actions/reference/security/secure-use",
            "https://github.com/aws-actions/configure-aws-credentials",
            "https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_create_for-idp_oidc.html",
            "https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html",
            "https://developer.hashicorp.com/terraform/tutorials/automation/automate-terraform",
            "https://developer.hashicorp.com/terraform/language/backend/s3",
            "https://docs.aws.amazon.com/AmazonECR/latest/userguide/image-tag-mutability.html",
        )
        for url in urls:
            self.assertIn(url, self.source)

    def test_readme_documents_oidc_bootstrap_and_no_long_lived_keys(self):
        self.assertIn("repo:JulienDira/big_data_platform:environment:dev", self.source)
        self.assertIn("GitHub Environment `dev`", self.source)
        self.assertIn("use_lockfile=true", self.source)
        self.assertIn("July 15, 2026", self.source)
        self.assertIn("Do not configure `AWS_ACCESS_KEY_ID`", self.source)
        self.assertIn("`AWS_SECRET_ACCESS_KEY`", self.source)

    def test_readme_documents_runtime_proof_cleanup_and_cost_control(self):
        for heading in (
            "## One-time bootstrap",
            "## GitHub Environment variables",
            "## Push-to-main flow",
            "## Runtime proof checks",
            "## Cleanup and cost control",
            "## Missing bootstrap behavior",
        ):
            self.assertIn(heading, self.source)
        self.assertIn("build/aws-runtime-evidence.json", self.source)
        self.assertIn("set ECS producer desired count back to `0`", self.source)
        self.assertIn("stop the Raw Glue Streaming job run", self.source)


if __name__ == "__main__":
    unittest.main()
