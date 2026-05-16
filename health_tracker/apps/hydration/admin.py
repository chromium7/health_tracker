"""Admin configuration for the hydration app."""

from django.contrib import admin

from health_tracker.apps.hydration.models import WaterIntakeLog


@admin.register(WaterIntakeLog)
class WaterIntakeLogAdmin(admin.ModelAdmin):
    """Admin for ``WaterIntakeLog``."""

    list_display = ["patient", "volume_ml", "created_at"]
    list_filter = ["patient"]
    search_fields = ["patient__username"]
