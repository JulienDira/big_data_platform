import base64
import importlib.util
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "infra/scripts/package-aws-artifacts.py"
SPEC = importlib.util.spec_from_file_location("package_aws_artifacts", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class AwsArtifactPackagingTest(unittest.TestCase):
    def test_packages_glue_and_lambda_artifacts_with_expected_layout(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "aws-artifacts"
            result = MODULE.package_artifacts(ROOT, output_dir)

            glue_dir = output_dir / "glue"
            lambda_dir = output_dir / "lambda"

            self.assertTrue((glue_dir / "jobs/raw-consumer/aws.py").is_file())
            self.assertTrue((glue_dir / "jobs/bronze-ingestion/aws.py").is_file())
            self.assertTrue((glue_dir / "jobs/silver-transformation/aws.py").is_file())
            self.assertTrue((glue_dir / "jobs/gold-indicators/aws.py").is_file())
            self.assertTrue((glue_dir / "contracts/market-candle-v1.avsc").is_file())
            self.assertTrue((glue_dir / "sql/market_indicators_latest.sql").is_file())

            with ZipFile(glue_dir / "python/jobs-utils.zip") as archive:
                names = set(archive.namelist())
            self.assertIn("utils/__init__.py", names)
            self.assertIn("utils/serving.py", names)

            with ZipFile(glue_dir / "python/serving-registry.zip") as archive:
                self.assertEqual(["registry.py"], archive.namelist())

            lambda_zip = lambda_dir / "aws-serving-api.zip"
            with ZipFile(lambda_zip) as archive:
                lambda_names = set(archive.namelist())
            self.assertIn("api_handler.py", lambda_names)
            self.assertIn("projection_handler.py", lambda_names)
            self.assertIn("serving_common.py", lambda_names)

            hash_file = lambda_dir / "aws-serving-api.zip.base64sha256"
            hash_value = hash_file.read_text(encoding="ascii").strip()
            self.assertEqual(result["lambda_source_hash"], hash_value)
            self.assertEqual(32, len(base64.b64decode(hash_value)))


if __name__ == "__main__":
    unittest.main()
