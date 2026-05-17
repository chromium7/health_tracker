"""Forms for the hydration app."""

from __future__ import annotations

from datetime import date, timedelta

from django import forms
from django.utils import timezone

from health_tracker.apps.hydration.models import WaterIntakeLog
from health_tracker.apps.hydration.utils import MAX_VOLUME_ML, MIN_VOLUME_ML


class WaterEntryForm(forms.Form):
    """Capture a single water-intake event.

    The form drives the in-line 'Add a drink' input on the water page.
    Validation enforces a positive, reasonable volume range so a
    malicious or accidental large value cannot be persisted.
    """

    volume_ml = forms.IntegerField(
        min_value=MIN_VOLUME_ML,
        max_value=MAX_VOLUME_ML,
        label="Volume (ml)",
    )
    notes = forms.CharField(required=False, widget=forms.Textarea)

    def clean_volume_ml(self) -> int:
        """Return the cleaned positive volume.

        Returns:
            The validated integer.
        """
        return int(self.cleaned_data["volume_ml"])

    def clean_notes(self) -> str:
        return (self.cleaned_data.get("notes") or "").strip()


class WaterEntryEditForm(forms.Form):
    """Edit an existing ``WaterIntakeLog``: volume, timestamp and notes."""

    timestamp = forms.DateTimeField(widget=forms.DateTimeInput(attrs={"type": "datetime-local"}))
    volume_ml = forms.IntegerField(min_value=MIN_VOLUME_ML, max_value=MAX_VOLUME_ML)
    notes = forms.CharField(required=False, widget=forms.Textarea)

    @classmethod
    def initial_for(cls, log: WaterIntakeLog) -> dict:
        """Return the initial form data for an existing log."""
        return {
            "timestamp": timezone.localtime(log.created_at).strftime("%Y-%m-%dT%H:%M"),
            "volume_ml": log.volume_ml,
            "notes": log.notes,
        }

    def clean_notes(self) -> str:
        return (self.cleaned_data.get("notes") or "").strip()

    def apply(self, log: WaterIntakeLog) -> WaterIntakeLog:
        """Persist the cleaned form data onto ``log``."""
        log.volume_ml = self.cleaned_data["volume_ml"]
        log.created_at = self.cleaned_data["timestamp"]
        log.notes = self.cleaned_data["notes"]
        log.save()
        return log


def default_history_range(today: date | None = None) -> tuple[date, date]:
    """Return the default 30-day range for an unbound history form.

    Args:
        today: Reference date; defaults to today.

    Returns:
        A ``(start, end)`` tuple where ``start`` is 29 days before
        ``end`` and ``end`` is today.
    """
    end = today or date.today()
    return end - timedelta(days=29), end
