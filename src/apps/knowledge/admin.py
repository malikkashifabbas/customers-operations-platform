"""Knowledge base in the admin: read-only, because documents come from seed_knowledge (which also embeds them)."""

from django.contrib import admin
from django.db.models import Count

from .models import KnowledgeChunk, KnowledgeDocument


class ReadOnlyAdminMixin:
    # Editing text here would leave the old embedding behind, so search would match text that no longer exists.
    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


class KnowledgeChunkInline(ReadOnlyAdminMixin, admin.TabularInline):
    model = KnowledgeChunk
    fields = readonly_fields = ["position", "section", "text"]
    ordering = ["position"]
    extra = 0
    can_delete = False
    show_change_link = True


@admin.register(KnowledgeDocument)
class KnowledgeDocumentAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = ["title", "slug", "tenant", "version", "chunk_count", "updated_at"]
    list_filter = ["tenant"]
    search_fields = ["title", "slug"]
    list_select_related = ["tenant"]
    inlines = [KnowledgeChunkInline]

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(chunk_count=Count("chunks"))

    @admin.display(ordering="chunk_count", description="chunks")
    def chunk_count(self, obj):
        return obj.chunk_count


@admin.register(KnowledgeChunk)
class KnowledgeChunkAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = ["document", "position", "section", "tenant"]
    list_filter = ["tenant", "document"]
    search_fields = ["text", "section"]  # handy to check whether a policy sentence was indexed at all
    list_select_related = ["document", "tenant"]
    exclude = ["embedding"]  # 384 numbers mean nothing to a person and make the page heavy
