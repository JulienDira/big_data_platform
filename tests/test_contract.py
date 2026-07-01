import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ContractTest(unittest.TestCase):
    def test_canonical_contract_has_required_identity_and_metrics(self):
        contract = json.loads(
            (ROOT / "contracts/market-candle/v1.avsc").read_text(encoding="utf-8")
        )
        fields = {field["name"] for field in contract["fields"]}
        self.assertTrue(
            {
                "event_id",
                "source",
                "symbol",
                "interval",
                "open_time",
                "close_time",
                "open",
                "high",
                "low",
                "close",
                "volume",
                "ingested_at",
            }.issubset(fields)
        )

    def test_python_sources_do_not_contain_private_network_addresses(self):
        forbidden = ("192.168.", "172.20.")
        extensions = ("*.py", "*.yml", "*.xml", "*.conf", "*.sh")
        for directory in ("apps", "jobs", "infra"):
            for extension in extensions:
                for path in (ROOT / directory).rglob(extension):
                    source = path.read_text(encoding="utf-8")
                    for value in forbidden:
                        self.assertNotIn(value, source, str(path))

    def test_cadrage_keeps_aws_target_without_rds_or_postgresql(self):
        cadrage = (ROOT / "cadrage.md").read_text(encoding="utf-8")
        terraform_sources = "\n".join(
            path.read_text(encoding="utf-8")
            for path in (ROOT / "infra/aws").rglob("*.tf")
        )

        self.assertIn("PostgreSQL reste une cible de serving on-premise", cadrage)
        self.assertIn("S3", cadrage)
        self.assertIn("Glue Data Catalog", cadrage)
        self.assertIn("Athena", cadrage)
        self.assertNotIn("aws_db", terraform_sources)
        self.assertNotIn("aws_rds", terraform_sources)
        self.assertNotIn("postgresql", terraform_sources.lower())
        self.assertNotIn("postgres", terraform_sources.lower())

    def test_aws_serving_surface_is_static_terraform_only(self):
        terraform_sources = "\n".join(
            path.read_text(encoding="utf-8")
            for path in (ROOT / "infra/aws/serving").rglob("*.tf")
        )

        self.assertIn("aws_dynamodb_table", terraform_sources)
        self.assertIn("aws_lambda_function", terraform_sources)
        self.assertIn("aws_apigatewayv2_api", terraform_sources)
        self.assertIn("aws_cognito_user_pool", terraform_sources)
        self.assertIn("aws_budgets_budget", terraform_sources)

    def test_gold_and_serving_entrypoints_use_common_helpers(self):
        gold_main = (ROOT / "jobs/gold-indicators/main.py").read_text(encoding="utf-8")
        gold_aws = (ROOT / "jobs/gold-indicators/aws.py").read_text(encoding="utf-8")
        serving_main = (ROOT / "jobs/serving-datamart/main.py").read_text(encoding="utf-8")

        self.assertIn("from utils.indicators import calculate_indicators", gold_main)
        self.assertIn("from utils.indicators import calculate_indicators", gold_aws)
        self.assertIn("materialize_serving_tables", gold_aws)
        self.assertIn("materialize_serving_tables", serving_main)


if __name__ == "__main__":
    unittest.main()
