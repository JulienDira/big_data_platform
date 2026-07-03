import importlib.util
import json
import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path


PYSPARK_AVAILABLE = importlib.util.find_spec("pyspark") is not None
ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "tests" / "fixtures" / "golden"

if PYSPARK_AVAILABLE:
    sys.path.insert(0, str(ROOT / "jobs"))
    sys.path.insert(0, str(ROOT / "jobs" / "serving-datamart"))

    from pyspark.sql.functions import to_date

    from registry import get_serving_tables, read_table_sql, render_sql
    from spark_test_utils import create_local_spark
    from utils.indicators import calculate_indicators
    from utils.serving import build_serving_render_context, materialize_serving_tables
else:
    create_local_spark = None


def _load_json(name):
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def _format_timestamp(value):
    return value.strftime("%Y-%m-%d %H:%M:%S")


def _format_date(value):
    return value.isoformat()


@unittest.skipUnless(PYSPARK_AVAILABLE, "PySpark is not available")
class GoldRestitutionGoldenTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spark = create_local_spark("gold-restitution-golden-test")
        cls.silver_fixture = _load_json("silver_candles.json")
        cls.expected = _load_json("expected_outputs.json")

    @classmethod
    def tearDownClass(cls):
        cls.spark.stop()

    def test_gold_indicators_match_golden_silver_fixture(self):
        gold = self._gold_from_fixture()
        result = gold.filter("interval = '1m'").orderBy("open_time").collect()

        self.assertEqual(30, len(result))
        self.assertEqual(34, gold.count())
        self._assert_row_matches(result[-1], self.expected["gold_last_1m"])

    def test_serving_tables_match_golden_gold_fixture(self):
        frames = self._serving_frames()

        self.assertEqual(34, frames["market_indicators"].count())
        market_last = (
            frames["market_indicators"]
            .filter("symbol = 'BTCUSDC' AND interval = '1m'")
            .orderBy("open_time")
            .collect()[-1]
        )
        self.assertEqual("2025-01-02 00:00:00", _format_timestamp(market_last.loaded_at))

        latest = self._single_row(
            frames["market_indicators_latest"].filter(
                "symbol = 'BTCUSDC' AND interval = '1m'"
            )
        )
        self._assert_row_matches(latest, self.expected["serving_latest_1m"])

        signal = (
            frames["market_multitimeframe_signals"]
            .filter("symbol = 'BTCUSDC'")
            .orderBy("open_time")
            .collect()[-1]
        )
        self._assert_row_matches(signal, self.expected["serving_signal_latest"])

        daily_summary = self._single_row(frames["market_daily_summary"])
        self._assert_row_matches(daily_summary, self.expected["serving_daily_summary"])

    def _gold_from_fixture(self):
        rows = self._silver_rows()
        silver = self.spark.createDataFrame(rows)
        return calculate_indicators(silver).withColumn("event_date", to_date("open_time"))

    def _serving_frames(self):
        processing_timestamp = self.expected["processing_timestamp"].replace("T", " ")
        context = build_serving_render_context(
            base_interval="1m",
            context_intervals=["15m", "1h"],
            processing_timestamp=f"TIMESTAMP '{processing_timestamp}'",
        )
        return {
            table.name: frame
            for table, frame in materialize_serving_tables(
                self._gold_from_fixture(),
                get_serving_tables(),
                read_table_sql,
                render_sql,
                context,
            )
        }

    def _silver_rows(self):
        fixture = self.silver_fixture
        symbol = fixture["symbol"]
        base = fixture["base_series"]
        start = datetime.fromisoformat(base["start"])
        rows = []

        for index, value in enumerate(base["open_close_values"]):
            open_time = start + timedelta(minutes=index * base["step_minutes"])
            close_time = open_time + timedelta(seconds=59)
            rows.append(
                {
                    "symbol": symbol,
                    "interval": base["interval"],
                    "open_time": open_time,
                    "close_time": close_time,
                    "open": float(value),
                    "high": float(value) + 1.0,
                    "low": float(value) - 1.0,
                    "close": float(value),
                    "volume": float(base["volume"]),
                }
            )

        for candle in fixture["context_candles"]:
            rows.append(
                {
                    "symbol": symbol,
                    "interval": candle["interval"],
                    "open_time": datetime.fromisoformat(candle["open_time"]),
                    "close_time": datetime.fromisoformat(candle["close_time"]),
                    "open": float(candle["open"]),
                    "high": float(candle["high"]),
                    "low": float(candle["low"]),
                    "close": float(candle["close"]),
                    "volume": float(candle["volume"]),
                }
            )

        return rows

    def _single_row(self, frame):
        rows = frame.collect()
        self.assertEqual(1, len(rows))
        return rows[0]

    def _assert_row_matches(self, row, expected):
        for field, expected_value in expected.items():
            actual_value = getattr(row, field)
            if isinstance(expected_value, float):
                self.assertAlmostEqual(expected_value, actual_value, delta=0.000001, msg=field)
            elif field.endswith("_time") or field.endswith("_at"):
                self.assertEqual(expected_value, _format_timestamp(actual_value), field)
            elif field == "event_date":
                self.assertEqual(expected_value, _format_date(actual_value), field)
            else:
                self.assertEqual(expected_value, actual_value, field)


if __name__ == "__main__":
    unittest.main()
