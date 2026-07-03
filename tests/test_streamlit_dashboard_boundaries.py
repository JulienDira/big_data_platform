import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STREAMLIT_PATH = ROOT / "apps/streamlit-dashboard"


class StreamlitDashboardBoundaryTest(unittest.TestCase):
    def test_streamlit_dashboard_does_not_import_aws_sdks(self):
        combined = "\n".join(
            path.read_text(encoding="utf-8")
            for path in STREAMLIT_PATH.rglob("*")
            if path.is_file() and path.suffix in {".py", ".txt", ".toml"}
        )

        forbidden = (
            "boto3",
            "botocore",
            "aioboto3",
            "awswrangler",
            "s3fs",
        )
        for value in forbidden:
            self.assertNotIn(value, combined)

    def test_streamlit_dashboard_calls_api_gateway_configuration_only(self):
        app = (STREAMLIT_PATH / "app.py").read_text(encoding="utf-8")

        self.assertIn("API_BASE_URL", app)
        self.assertIn("COGNITO_DOMAIN", app)
        self.assertNotIn("dynamodb", app.lower())
        self.assertNotIn("athena", app.lower())
        self.assertNotIn("glue", app.lower())


if __name__ == "__main__":
    unittest.main()
