from __future__ import annotations

import json
import logging
import os
import time

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


def build_kinesis_client(region_name: str):
    import boto3

    return boto3.client("kinesis", region_name=region_name)


def encode_candle(candle: dict) -> bytes:
    return json.dumps(
        candle,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def build_kinesis_record(candle: dict) -> dict:
    return {
        "Data": encode_candle(candle),
        "PartitionKey": build_partition_key(candle),
    }


def batched(records: list[dict], batch_size: int) -> list[list[dict]]:
    return [
        records[index : index + batch_size]
        for index in range(0, len(records), batch_size)
    ]


def publish_records(
    client,
    stream_name: str,
    records: list[dict],
    batch_size: int,
) -> None:
    for batch in batched(records, batch_size):
        response = client.put_records(StreamName=stream_name, Records=batch)
        failed_count = int(response.get("FailedRecordCount", 0))
        if failed_count:
            errors = [
                result.get("ErrorCode", "UnknownError")
                for result in response.get("Records", [])
                if "ErrorCode" in result
            ]
            sample = ",".join(errors[:3])
            raise RuntimeError(
                f"Kinesis put_records failed for {failed_count} records: {sample}"
            )


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
                    records.append(build_kinesis_record(candle))
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
