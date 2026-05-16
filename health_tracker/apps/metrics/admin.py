"""Admin configuration for the metrics app."""

from django.contrib import admin

from health_tracker.apps.metrics.models import HealthMetric


@admin.register(HealthMetric)
class HealthMetricAdmin(admin.ModelAdmin):
    """Admin for ``HealthMetric``."""

    list_display = ["patient", "metric_type", "value", "created_at"]
    list_filter = ["metric_type", "patient"]
    search_fields = ["patient__username"]
