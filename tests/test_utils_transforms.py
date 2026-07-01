import importlib.util
import sys
import unittest
from pathlib import Path


PYSPARK_AVAILABLE = importlib.util.find_spec("pyspark") is not None
ROOT = Path(__file__).resolve().parents[1]

if PYSPARK_AVAILABLE:
    sys.path.insert(0, str(ROOT / "jobs"))

    from pyspark.sql.types import StringType, StructField, StructType

    from spark_test_utils import create_local_spark
    from utils.bronze import build_bronze_rejected
    from utils.dedup import latest_by_key
    from utils.market_schema import GOLD_SOURCE_COLUMNS, SILVER_COLUMNS
    from utils.quality import apply_silver_quality_rules
    from utils.silver import build_silver
else:
    create_local_spark = None


@unittest.skipUnless(PYSPARK_AVAILABLE, "PySpark is not available")
class UtilsTransformsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spark = create_local_spark("utils-transforms-test")

    @classmethod
    def tearDownClass(cls):
        cls.spark.stop()

    def test_latest_by_key_keeps_newest_record(self):
        frame = self.spark.createDataFrame(
            [
                {
                    "symbol": "BTCUSDC",
                    "interval": "1m",
                    "open_time": "2026-01-01 00:00:00",
                    "ingested_at": "2026-01-01 00:00:01",
                    "event_id": "old",
                },
                {
                    "symbol": "BTCUSDC",
                    "interval": "1m",
                    "open_time": "2026-01-01 00:00:00",
                    "ingested_at": "2026-01-01 00:00:02",
                    "event_id": "new",
                },
            ]
        )

        result = latest_by_key(
            frame,
            key_columns=["symbol", "interval", "open_time"],
            order_columns=["ingested_at", "event_id"],
        )

        self.assertEqual(["new"], [row.event_id for row in result.collect()])

    def test_apply_silver_quality_rules_filters_invalid_candles(self):
        valid = {
            "event_id": "valid",
            "source": "binance",
            "symbol": "BTCUSDC",
            "interval": "1m",
            "open_time": "2026-01-01 00:00:00",
            "close_time": "2026-01-01 00:00:59",
            "open": 10.0,
            "high": 12.0,
            "low": 9.0,
            "close": 11.0,
            "volume": 1.0,
            "quote_asset_volume": 11.0,
            "number_of_trades": 1,
            "taker_buy_base_asset_volume": 0.5,
            "taker_buy_quote_asset_volume": 5.5,
            "is_closed": True,
            "ingested_at": "2026-01-01 00:01:00",
            "event_date": "2026-01-01",
        }
        invalid_open = dict(valid, event_id="invalid_open", open=-1.0)
        not_closed = dict(valid, event_id="not_closed", is_closed=False)

        frame = self.spark.createDataFrame([valid, invalid_open, not_closed])
        result = apply_silver_quality_rules(frame)

        self.assertEqual(["valid"], [row.event_id for row in result.collect()])

    def test_build_silver_keeps_expected_contract_for_gold(self):
        base = {
            "event_id": "old",
            "source": "binance-rest",
            "symbol": "BTCUSDC",
            "interval": "1m",
            "open_time": "2026-01-01 00:00:00",
            "close_time": "2026-01-01 00:00:59",
            "open": 10.0,
            "high": 12.0,
            "low": 9.0,
            "close": 11.0,
            "volume": 1.0,
            "quote_asset_volume": 11.0,
            "number_of_trades": 1,
            "taker_buy_base_asset_volume": 0.5,
            "taker_buy_quote_asset_volume": 5.5,
            "is_closed": True,
            "ingested_at": "2026-01-01 00:01:00",
            "event_date": "2026-01-01",
        }
        newer = dict(base, event_id="new", ingested_at="2026-01-01 00:02:00")

        result = build_silver(self.spark.createDataFrame([base, newer]))

        self.assertEqual(SILVER_COLUMNS, result.columns)
        self.assertTrue(set(GOLD_SOURCE_COLUMNS).issubset(result.columns))
        self.assertEqual(["new"], [row.event_id for row in result.collect()])

    def test_build_bronze_rejected_preserves_raw_envelope(self):
        schema = StructType(
            [
                StructField("source", StringType(), True),
                StructField("stream_name", StringType(), True),
                StructField("partition_key", StringType(), True),
                StructField("sequence_number", StringType(), True),
                StructField("value", StringType(), True),
                StructField("data", StringType(), True),
            ]
        )
        frame = self.spark.createDataFrame(
            [("kinesis", "market-candles", "BTCUSDC|1m", "1", "bad", None)],
            schema,
        )

        result = build_bronze_rejected(frame)
        row = result.collect()[0]

        self.assertEqual("market-candles", row.stream_name)
        self.assertEqual("BTCUSDC|1m", row.partition_key)
        self.assertEqual("avro_decode_failed", row.bronze_error_reason)


if __name__ == "__main__":
    unittest.main()
