import importlib.util
import os
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "jobs/utils/env.py"
SPEC = importlib.util.spec_from_file_location("env_utils", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class EnvUtilsTest(unittest.TestCase):
    def test_required_env_raises_clear_error_when_missing(self):
        name = "BIG_DATA_PLATFORM_TEST_MISSING_ENV"
        previous = os.environ.pop(name, None)
        try:
            with self.assertRaisesRegex(RuntimeError, name):
                MODULE.required_env(name)
        finally:
            if previous is not None:
                os.environ[name] = previous

    def test_csv_env_splits_non_empty_values(self):
        name = "BIG_DATA_PLATFORM_TEST_CSV_ENV"
        previous = os.environ.get(name)
        os.environ[name] = "1m, 15m,,1h"
        try:
            self.assertEqual(["1m", "15m", "1h"], MODULE.csv_env(name))
        finally:
            if previous is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = previous


if __name__ == "__main__":
    unittest.main()

