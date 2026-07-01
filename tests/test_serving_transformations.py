import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "jobs"))

from utils.serving import build_serving_render_context


class ServingTransformationsTest(unittest.TestCase):
    def test_build_serving_render_context_maps_timeframes(self):
        context = build_serving_render_context(
            base_interval="1m",
            context_intervals=["15m", "1h"],
        )

        self.assertEqual("gold_market_indicators", context["source_view"])
        self.assertEqual("1m", context["base_interval"])
        self.assertEqual("15m", context["context_interval_1"])
        self.assertEqual("1h", context["context_interval_2"])
        self.assertEqual("current_timestamp()", context["processing_timestamp"])

    def test_build_serving_render_context_requires_two_context_intervals(self):
        with self.assertRaisesRegex(RuntimeError, "exactly two values"):
            build_serving_render_context(
                base_interval="1m",
                context_intervals=["15m"],
            )


if __name__ == "__main__":
    unittest.main()
