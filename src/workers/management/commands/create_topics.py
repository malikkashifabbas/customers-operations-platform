"""Create the Kafka topics listed in infra/eventbus/topics.py (Kafka auto-create is off on purpose)."""

from confluent_kafka.admin import AdminClient, NewTopic
from django.core.management.base import BaseCommand

from config.env import env
from infra.eventbus.topics import TOPICS


class Command(BaseCommand):
    help = "Create the Kafka topics OpsPilot needs (safe to run again)."

    def handle(self, *args, **options):
        admin = AdminClient({"bootstrap.servers": env.kafka_bootstrap_servers})
        existing = set(admin.list_topics(timeout=10).topics)
        missing = [
            NewTopic(name, num_partitions=partitions, replication_factor=1)
            for name, partitions in TOPICS.items()
            if name not in existing
        ]
        if missing:
            for name, future in admin.create_topics(missing).items():
                future.result()
                self.stdout.write(self.style.SUCCESS(f"created {name}"))
        for name, partitions in TOPICS.items():
            if name in existing:
                self.stdout.write(f"exists  {name} ({partitions} partitions)")
