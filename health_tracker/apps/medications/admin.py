"""Admin configuration for the medications app."""

from django.contrib import admin

from health_tracker.apps.medications.models import Medication, MedicationLog


@admin.register(Medication)
class MedicationAdmin(admin.ModelAdmin):
    """Admin for ``Medication``."""

    list_display = ["name", "patient", "dosage", "is_active", "stop_reason", "stopped_at"]
    list_filter = ["is_active", "stop_reason", "patient"]
    search_fields = ["name", "patient__username"]


@admin.register(MedicationLog)
class MedicationLogAdmin(admin.ModelAdmin):
    """Admin for ``MedicationLog``."""

    list_display = ["medication", "taken_at"]
    list_filter = ["medication__patient"]
    search_fields = ["medication__name", "medication__patient__username"]
