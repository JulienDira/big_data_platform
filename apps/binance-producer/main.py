import logging
import os
from pathlib import Path
import time

import requests
from confluent_kafka import SerializingProducer
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroSerializer
from confluent_kafka.serialization import StringSerializer

from common import build_partition_key, csv_env, fetch_latest, required_env


logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(message)s",
)
LOGGER = logging.getLogger("binance-producer")


def load_schema() -> str:
    return Path(required_env("CONTRACT_PATH")).read_text(encoding="utf-8")


def delivery_report(error, message) -> None:
    if error:
        LOGGER.error("Kafka delivery failed: %s", error)
    else:
        LOGGER.debug("Delivered to %s[%s]@%s", message.topic(), message.partition(), message.offset())


def build_producer() -> SerializingProducer:
    registry = SchemaRegistryClient({"url": required_env("SCHEMA_REGISTRY_URL")})
    serializer = AvroSerializer(
        registry,
        load_schema(),
        lambda record, _: record,
        {"auto.register.schemas": True},
    )
    return SerializingProducer(
        {
            "bootstrap.servers": required_env("KAFKA_BOOTSTRAP_SERVERS"),
            "key.serializer": StringSerializer("utf_8"),
            "value.serializer": serializer,
            "enable.idempotence": True,
            "acks": "all",
            "compression.type": "snappy",
        }
    )


def main() -> None:
    topic = required_env("KAFKA_TOPIC")
    symbols = csv_env("MARKET_SYMBOLS")
    intervals = csv_env("MARKET_INTERVALS")
    poll_seconds = int(os.getenv("PRODUCER_POLL_SECONDS", "15"))
    producer = build_producer()
    session = requests.Session()
    base_url = required_env("BINANCE_BASE_URL").rstrip("/")
    last_event_ids: set[str] = set()

    while True:
        for symbol in symbols:
            for interval in intervals:
                try:
                    candle = fetch_latest(session, base_url, symbol, interval.lower())
                    if candle["event_id"] in last_event_ids:
                        continue
                    producer.produce(
                        topic=topic,
                        key=build_partition_key(candle),
                        value=candle,
                        on_delivery=delivery_report,
                    )
                    producer.poll(0)
                    last_event_ids.add(candle["event_id"])
                    LOGGER.info("Published %s", candle["event_id"])
                except Exception:
                    LOGGER.exception("Failed to publish %s/%s", symbol, interval)
        producer.flush(10)
        time.sleep(poll_seconds)


if __name__ == "__main__":
    main()
