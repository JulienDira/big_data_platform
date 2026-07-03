from __future__ import annotations

import logging
import os
from pathlib import Path
import time

from avro_codec import encode_record, load_schema
from common import (
    build_partition_key,
    csv_env,
    fetch_latest,
    positive_int_env,
    required_env,
)


logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(message)s",
)
LOGGER = logging.getLogger("binance-producer-aws")


def load_contract() -> dict:
    return load_schema(Path(required_env("CONTRACT_PATH")))


def build_kinesis_client(region_name: str):
    import boto3

    return boto3.client("kinesis", region_name=region_name)


def encode_candle(candle: dict, schema: dict | None = None) -> bytes:
    return encode_record(candle, schema or load_contract())


def build_kinesis_record(candle: dict, schema: dict | None = None) -> dict:
    return {
        "Data": encode_candle(candle, schema),
        "PartitionKey": build_partition_key(candle),
    }


def batched(records: list[dict], batch_size: int) -> list[list[dict]]:
    return [
        records[index : index + batch_size]
        for index in range(0, len(records), batch_size)
    ]


def failed_records_from_response(records: list[dict], response: dict) -> list[dict]:
    results = response.get("Records", [])
    return [
        record
        for record, result in zip(records, results)
        if "ErrorCode" in result
    ]


def error_sample(response: dict) -> str:
    errors = [
        result.get("ErrorCode", "UnknownError")
        for result in response.get("Records", [])
        if "ErrorCode" in result
    ]
    return ",".join(errors[:3])


def publish_records(
    client,
    stream_name: str,
    records: list[dict],
    batch_size: int,
    *,
    max_attempts: int = 3,
    retry_backoff_seconds: float = 1.0,
) -> None:
    for batch in batched(records, batch_size):
        pending = batch
        attempt = 1
        while pending:
            response = client.put_records(StreamName=stream_name, Records=pending)
            failed_count = int(response.get("FailedRecordCount", 0))
            if failed_count == 0:
                break

            failed = failed_records_from_response(pending, response)
            sample = error_sample(response)
            if not failed or attempt >= max_attempts:
                raise RuntimeError(
                    f"Kinesis put_records failed for {failed_count} records: {sample}"
                )

            LOGGER.warning(
                "Retrying %s failed Kinesis records after attempt %s/%s: %s",
                len(failed),
                attempt,
                max_attempts,
                sample,
            )
            time.sleep(retry_backoff_seconds * attempt)
            pending = failed
            attempt += 1


def main() -> None:
    import requests

    stream_name = required_env("KINESIS_STREAM_NAME")
    region_name = required_env("AWS_REGION")
    symbols = csv_env("MARKET_SYMBOLS")
    intervals = csv_env("MARKET_INTERVALS")
    poll_seconds = positive_int_env("PRODUCER_POLL_SECONDS", 15)
    batch_size = positive_int_env("KINESIS_PUBLISH_BATCH_SIZE", 500, maximum=500)

    client = build_kinesis_client(region_name)
    session = requests.Session()
    base_url = required_env("BINANCE_BASE_URL").rstrip("/")
    schema = load_contract()
    last_event_ids: set[str] = set()

    while True:
        records = []
        event_ids = []
        for symbol in symbols:
            for interval in intervals:
                try:
                    candle = fetch_latest(session, base_url, symbol, interval.lower())
                    if candle["event_id"] in last_event_ids:
                        continue
                    records.append(build_kinesis_record(candle, schema))
                    event_ids.append(candle["event_id"])
                except Exception:
                    LOGGER.exception("Failed to fetch %s/%s", symbol, interval)

        if records:
            try:
                publish_records(client, stream_name, records, batch_size)
                last_event_ids.update(event_ids)
                LOGGER.info("Published %s Kinesis records", len(records))
            except Exception:
                LOGGER.exception("Failed to publish Kinesis batch")

        time.sleep(poll_seconds)


if __name__ == "__main__":
    main()
