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


if __name__ == "__main__":
    unittest.main()
