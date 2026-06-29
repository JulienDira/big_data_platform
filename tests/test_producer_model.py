import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT / "apps/binance-producer/model.py"
SPEC = importlib.util.spec_from_file_location("producer_model", MODEL_PATH)
MODEL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODEL)


class ProducerModelTest(unittest.TestCase):
    def test_binance_row_is_normalized_to_canonical_contract(self):
        row = [
            1_700_000_000_000,
            "10.0",
            "12.0",
            "9.0",
            "11.0",
            "42.0",
            1_700_000_059_999,
            "450.0",
            17,
            "20.0",
            "215.0",
            "0",
        ]
        candle = MODEL.normalize_kline(
            "BTCUSDC", "1m", row, now_ms=1_700_000_060_000
        )

        self.assertEqual("binance:BTCUSDC:1m:1700000000000", candle["event_id"])
        self.assertEqual(11.0, candle["close"])
        self.assertEqual(17, candle["number_of_trades"])
        self.assertTrue(candle["is_closed"])


if __name__ == "__main__":
    unittest.main()

