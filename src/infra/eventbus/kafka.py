"""Kafka clients built from settings in one place."""

from confluent_kafka import Consumer, Producer

from config.env import env


def make_producer() -> Producer:
    # Idempotent producer: a network retry can never write the same message to Kafka twice.
    return Producer({"bootstrap.servers": env.kafka_bootstrap_servers, "enable.idempotence": True, "acks": "all"})


def make_consumer(group_id: str) -> Consumer:
    return Consumer({
        "bootstrap.servers": env.kafka_bootstrap_servers,
        "group.id": group_id,
        "enable.auto.commit": False,  # commit only after the work is saved, so a crash replays instead of losing
        "auto.offset.reset": "earliest",
    })
