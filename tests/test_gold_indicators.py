import importlib.util
import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path


PYSPARK_AVAILABLE = importlib.util.find_spec("pyspark") is not None
ROOT = Path(__file__).resolve().parents[1]

if PYSPARK_AVAILABLE:
    sys.path.insert(0, str(ROOT / "jobs"))
    from pyspark.sql import SparkSession

    from utils.indicators import calculate_indicators
else:
    SparkSession = None


@unittest.skipUnless(PYSPARK_AVAILABLE, "PySpark is not available")
class GoldIndicatorsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spark = (
            SparkSession.builder.master("local[1]")
            .appName("gold-indicators-test")
            .config("spark.ui.enabled", "false")
            .config("spark.eventLog.enabled", "false")
            .config("spark.hadoop.fs.defaultFS", "file:///")
            .config("spark.sql.warehouse.dir", "/tmp/spark-warehouse")
            .getOrCreate()
        )

    @classmethod
    def tearDownClass(cls):
        cls.spark.stop()

    def test_indicators_are_deterministic_for_increasing_prices(self):
        start = datetime(2025, 1, 1)
        rows = [
            {
                "symbol": "BTCUSDC",
                "interval": "1m",
                "open_time": start + timedelta(minutes=index),
                "close_time": start + timedelta(minutes=index, seconds=59),
                "open": float(value),
                "high": float(value) + 1.0,
                "low": float(value) - 1.0,
                "close": float(value),
                "volume": 10.0,
            }
            for index, value in enumerate(range(1, 31))
        ]
        frame = self.spark.createDataFrame(rows)

        result = calculate_indicators(frame).orderBy("open_time").collect()

        self.assertEqual(30, len(result))
        self.assertGreater(result[-1].ema_12, result[-1].ema_26)
        self.assertGreater(result[-1].macd, 0)
        self.assertEqual(100.0, result[-1].rsi_14)
        self.assertGreaterEqual(
            result[-1].bollinger_upper,
            result[-1].bollinger_middle,
        )


if __name__ == "__main__":
    unittest.main()
