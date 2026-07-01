import importlib.util
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_PATH = ROOT / "apps/binance-producer"
sys.path.insert(0, str(APP_PATH))
SPEC = importlib.util.spec_from_file_location("producer_aws", APP_PATH / "aws.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
from avro_codec import decode_record, load_schema


def normalize_fastavro_logical_values(record: dict) -> dict:
    normalized = dict(record)
    for field in ("open_time", "close_time", "ingested_at"):
        value = normalized[field]
        if isinstance(value, datetime):
            normalized[field] = int(value.replace(tzinfo=timezone.utc).timestamp() * 1000)
    return normalized


def canonical_candle() -> dict:
    return {
        "event_id": "binance:BTCUSDC:1m:1700000000000",
        "source": "binance-rest",
        "symbol": "BTCUSDC",
        "interval": "1m",
        "open_time": 1_700_000_000_000,
        "close_time": 1_700_000_059_999,
        "open": 10.0,
        "high": 12.0,
        "low": 9.0,
        "close": 11.0,
        "volume": 42.0,
        "quote_asset_volume": 450.0,
        "number_of_trades": 17,
        "taker_buy_base_asset_volume": 20.0,
        "taker_buy_quote_asset_volume": 215.0,
        "is_closed": True,
        "ingested_at": 1_700_000_060_000,
    }


class ProducerAwsTest(unittest.TestCase):
    def test_kinesis_record_uses_symbol_interval_partition_key(self):
        contract = load_schema(ROOT / "contracts/market-candle/v1.avsc")
        record = MODULE.build_kinesis_record(canonical_candle(), contract)

        self.assertEqual("BTCUSDC|1m", record["PartitionKey"])

    def test_kinesis_payload_matches_canonical_avro_fields(self):
        candle = canonical_candle()
        contract = load_schema(ROOT / "contracts/market-candle/v1.avsc")
        record = MODULE.build_kinesis_record(candle, contract)
        payload = normalize_fastavro_logical_values(decode_record(record["Data"], contract))
        contract_fields = {field["name"] for field in contract["fields"]}

        self.assertEqual(contract_fields, set(payload))
        self.assertEqual(candle, payload)
        with self.assertRaises(UnicodeDecodeError):
            record["Data"].decode("utf-8")

    def test_invalid_avro_payload_raises_clear_error(self):
        contract = load_schema(ROOT / "contracts/market-candle/v1.avsc")

        with self.assertRaisesRegex(ValueError, "Invalid Avro payload"):
            decode_record(b"not-avro", contract)

    def test_publish_records_batches_kinesis_calls(self):
        class FakeKinesisClient:
            def __init__(self):
                self.calls = []

            def put_records(self, **kwargs):
                self.calls.append(kwargs)
                return {
                    "FailedRecordCount": 0,
                    "Records": [{"SequenceNumber": "1", "ShardId": "shardId-000"}],
                }

        client = FakeKinesisClient()
        contract = load_schema(ROOT / "contracts/market-candle/v1.avsc")
        records = [
            MODULE.build_kinesis_record(canonical_candle(), contract) for _ in range(3)
        ]

        MODULE.publish_records(client, "market-candles", records, batch_size=2)

        self.assertEqual([2, 1], [len(call["Records"]) for call in client.calls])
        self.assertEqual(
            ["market-candles", "market-candles"],
            [call["StreamName"] for call in client.calls],
        )


if __name__ == "__main__":
    unittest.main()
