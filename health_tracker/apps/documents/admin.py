"""Admin configuration for the documents app."""

from django.contrib import admin

from health_tracker.apps.documents.models import Document


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    """Admin for ``Document``."""

    list_display = ["title", "patient", "uploaded_at"]
    list_filter = ["patient"]
    search_fields = ["title", "patient__username"]
