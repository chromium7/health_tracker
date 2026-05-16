"""Forms for the medications app."""

from __future__ import annotations

from django import forms
from django.utils import timezone

from health_tracker.apps.medications.models import Medication, MedicationLog


class MedicationStopForm(forms.Form):
    """Mark a medication as stopped with a reason and date.

    Applying the form sets ``is_active=False`` and records why and when.
    """

    stop_reason = forms.ChoiceField(choices=Medication.StopReason.choices)
    stopped_at = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    @classmethod
    def initial_data(cls) -> dict:
        """Default to today's local date."""
        return {"stopped_at": timezone.localdate().strftime("%Y-%m-%d")}

    def apply(self, medication: Medication) -> Medication:
        """Persist the stop event onto ``medication``."""
        medication.is_active = False
        medication.stop_reason = self.cleaned_data["stop_reason"]
        medication.stopped_at = self.cleaned_data["stopped_at"]
        medication.save(update_fields=["is_active", "stop_reason", "stopped_at"])
        return medication


class MedicationLogEditForm(forms.Form):
    """Edit the timestamp of an existing ``MedicationLog``.

    The medication itself is fixed once logged; only the time it was
    taken can be corrected (e.g., when a caregiver marks the dose
    after the patient actually took it).
    """

    timestamp = forms.DateTimeField(widget=forms.DateTimeInput(attrs={"type": "datetime-local"}))

    @classmethod
    def initial_for(cls, log: MedicationLog) -> dict:
        """Return the initial form data for an existing log."""
        return {"timestamp": timezone.localtime(log.taken_at).strftime("%Y-%m-%dT%H:%M")}

    def apply(self, log: MedicationLog) -> MedicationLog:
        """Persist the cleaned timestamp onto ``log``."""
        log.taken_at = self.cleaned_data["timestamp"]
        log.save()
        return log
