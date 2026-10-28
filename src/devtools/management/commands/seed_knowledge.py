"""Index the sample policy documents in devtools/knowledge/<tenant-slug>/*.md into the knowledge base (safe to run again)."""

from pathlib import Path

from django.core.management.base import BaseCommand

from apps.knowledge import services
from core.models import Tenant

KNOWLEDGE_DIR = Path(__file__).resolve().parents[2] / "knowledge"


class Command(BaseCommand):
    help = "Chunk + embed the sample policy documents for every tenant folder (only changed files are re-embedded)."

    def handle(self, *args, **options):
        for folder in sorted(p for p in KNOWLEDGE_DIR.iterdir() if p.is_dir()):
            tenant = Tenant.objects.filter(slug=folder.name).first()
            if tenant is None:
                self.stderr.write(f"skip {folder.name}: no tenant with this slug (run seed_data first)")
                continue
            slugs = set()
            for path in sorted(folder.glob("*.md")):
                document, outcome = services.ingest_document(
                    tenant=tenant, slug=path.stem, markdown=path.read_text(encoding="utf-8")
                )
                slugs.add(path.stem)
                self.stdout.write(f"  {tenant.slug}/{path.stem}: {outcome} ({document.chunks.count()} chunks)")
            removed = services.remove_documents_except(tenant=tenant, keep_slugs=slugs)
            if removed:
                self.stdout.write(f"  {tenant.slug}: removed {removed} rows of deleted documents")
        self.stdout.write(self.style.SUCCESS("knowledge base ready"))
