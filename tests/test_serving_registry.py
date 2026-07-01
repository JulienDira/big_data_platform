import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "jobs/serving-datamart/registry.py"
SPEC = importlib.util.spec_from_file_location("serving_registry", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class ServingRegistryTest(unittest.TestCase):
    def test_declared_tables_have_sql_files(self):
        tables = MODULE.get_serving_tables()
        self.assertEqual(4, len(tables))

        for table in tables:
            sql_path = ROOT / "jobs/serving-datamart/sql" / table.sql_file
            self.assertTrue(sql_path.exists(), table.sql_file)

    def test_declared_tables_include_aws_partition_contract(self):
        partitions = {
            table.name: table.partition_columns
            for table in MODULE.get_serving_tables()
        }

        self.assertEqual(("event_date", "symbol", "interval"), partitions["market_indicators"])
        self.assertEqual((), partitions["market_indicators_latest"])
        self.assertEqual((), partitions["market_multitimeframe_signals"])
        self.assertEqual(("event_date", "symbol"), partitions["market_daily_summary"])

    def test_sql_templates_render_without_placeholders(self):
        context = {
            "source_view": "gold_market_indicators",
            "base_interval": "1m",
            "context_interval_1": "15m",
            "context_interval_2": "1h",
            "processing_timestamp": "current_timestamp()",
        }

        for table in MODULE.get_serving_tables():
            rendered = MODULE.render_sql(MODULE.read_table_sql(table), context)
            self.assertNotIn("{{", rendered)
            self.assertNotIn("}}", rendered)


if __name__ == "__main__":
    unittest.main()
