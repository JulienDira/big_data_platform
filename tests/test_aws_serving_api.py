import importlib.util
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
APP_PATH = ROOT / "apps/aws-serving-api"
sys.path.insert(0, str(APP_PATH))

API_SPEC = importlib.util.spec_from_file_location(
    "aws_serving_api_handler", APP_PATH / "api_handler.py"
)
API_MODULE = importlib.util.module_from_spec(API_SPEC)
API_SPEC.loader.exec_module(API_MODULE)

PROJECTION_SPEC = importlib.util.spec_from_file_location(
    "aws_serving_projection_handler", APP_PATH / "projection_handler.py"
)
PROJECTION_MODULE = importlib.util.module_from_spec(PROJECTION_SPEC)
PROJECTION_SPEC.loader.exec_module(PROJECTION_MODULE)


class AwsServingApiTest(unittest.TestCase):
    def test_projection_maps_latest_row_to_dynamodb_item(self):
        row = {
            "symbol": "BTCUSDC",
            "interval": "1m",
            "open_time": "2025-01-01 00:00:00.000",
            "close_time": "2025-01-01 00:00:59.999",
            "open": "100.1",
            "high": "101.2",
            "low": "99.9",
            "close": "100.8",
            "volume": "42.5",
            "ema_12": "100.4",
            "ema_26": "100.2",
            "macd": "0.2",
            "rsi_14": "55.5",
            "bollinger_middle": "100.0",
            "bollinger_upper": "102.0",
            "bollinger_lower": "98.0",
            "event_date": "2025-01-01",
            "updated_at": "2025-01-01 00:01:02.000",
        }

        parsed = {
            field: PROJECTION_MODULE.parse_latest_value(field, value)
            for field, value in row.items()
        }
        item = PROJECTION_MODULE.latest_metric_row_to_item(
            parsed,
            ttl_days=7,
            now_epoch=1_700_000_000,
        )

        self.assertEqual({"S": "BTCUSDC"}, item["symbol"])
        self.assertEqual({"S": "1m"}, item["interval"])
        self.assertEqual({"N": "100.8"}, item["close"])
        self.assertEqual({"N": "1700604800"}, item["expires_at_epoch"])

    def test_history_query_rejects_missing_interval_before_aws_call(self):
        with patch.dict(os.environ, {"ATHENA_DATABASE": "trading_gold"}, clear=False):
            with self.assertRaisesRegex(API_MODULE.BadRequest, "interval"):
                API_MODULE.build_query("history", {"symbol": "BTCUSDC"}, 100)

    def test_history_query_uses_fixed_table_and_validated_filters(self):
        with patch.dict(os.environ, {"ATHENA_DATABASE": "trading_gold"}, clear=False):
            query = API_MODULE.build_query(
                "history",
                {
                    "symbol": "BTCUSDC",
                    "interval": "1m",
                    "from": "2025-01-01",
                    "to": "2025-01-02T12:30:00Z",
                },
                50,
            )

        self.assertIn('FROM "trading_gold"."market_indicators"', query)
        self.assertIn("symbol = 'BTCUSDC'", query)
        self.assertIn("interval = '1m'", query)
        self.assertIn("LIMIT 50", query)
        self.assertNotIn("{{", query)

    def test_athena_response_keeps_numbers_as_numbers(self):
        page = {
            "ResultSet": {
                "ResultSetMetadata": {
                    "ColumnInfo": [
                        {"Name": "symbol"},
                        {"Name": "close"},
                        {"Name": "signal_score"},
                        {"Name": "open_time"},
                    ]
                },
                "Rows": [
                    {
                        "Data": [
                            {"VarCharValue": "symbol"},
                            {"VarCharValue": "close"},
                            {"VarCharValue": "signal_score"},
                            {"VarCharValue": "open_time"},
                        ]
                    },
                    {
                        "Data": [
                            {"VarCharValue": "BTCUSDC"},
                            {"VarCharValue": "100.5"},
                            {"VarCharValue": "2"},
                            {"VarCharValue": "2025-01-01 00:00:00.000"},
                        ]
                    },
                ],
            }
        }

        response = API_MODULE.page_to_response("query-1", page)

        self.assertEqual("BTCUSDC", response["items"][0]["symbol"])
        self.assertEqual(100.5, response["items"][0]["close"])
        self.assertEqual(2, response["items"][0]["signal_score"])
        self.assertEqual("2025-01-01T00:00:00.000", response["items"][0]["open_time"])

    def test_lambda_sources_do_not_compute_indicators_or_import_spark(self):
        combined = "\n".join(
            path.read_text(encoding="utf-8")
            for path in APP_PATH.glob("*.py")
        )

        forbidden = (
            "SparkSession",
            "pyspark",
            "calculate_indicators",
            "rolling",
            "ewm",
        )
        for value in forbidden:
            self.assertNotIn(value, combined)


if __name__ == "__main__":
    unittest.main()
