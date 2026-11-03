"""Rebuild the Qdrant copy of the knowledge base from Postgres (first setup, or after Qdrant lost its data)."""

from django.core.management.base import BaseCommand

from apps.knowledge.models import KnowledgeDocument
from apps.knowledge.vector_sync import sync_document
from infra.vectorstore import qdrant


class Command(BaseCommand):
    help = "Copy every knowledge document from Postgres to Qdrant; safe to run again (no duplicates)."

    def add_arguments(self, parser):
        parser.add_argument("--tenant", help="only this tenant slug, e.g. demo-company")

    def handle(self, *args, **options):
        documents = KnowledgeDocument.objects.select_related("tenant").order_by("tenant__slug", "slug")
        if options["tenant"]:
            documents = documents.filter(tenant__slug=options["tenant"])
        total = 0
        for document in documents:
            points = sync_document(document_public_id=str(document.public_id))
            total += points
            self.stdout.write(f"  {document.tenant.slug}/{document.slug}: {points} points")
        self.stdout.write(self.style.SUCCESS(f"Qdrant has {qdrant.count()} points ({total} written now)"))
