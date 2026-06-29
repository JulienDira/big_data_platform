import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "jobs/raw-consumer/raw_config.py"
SPEC = importlib.util.spec_from_file_location("raw_consumer", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class RawConsumerConfigTest(unittest.TestCase):
    def test_global_checkpoint_path_is_stable(self):
        self.assertEqual(
            "/checkpoints/raw/binance/market_candles/global",
            MODULE.global_checkpoint_path("/checkpoints/raw/binance/market_candles/"),
        )


if __name__ == "__main__":
    unittest.main()
