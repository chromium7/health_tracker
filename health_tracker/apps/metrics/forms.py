"""Forms used to capture and edit health-metric readings."""

from __future__ import annotations

from typing import Any

from django import forms
from django.core.paginator import Page, Paginator
from django.utils import timezone

from health_tracker.apps.metrics.models import HealthMetric
from health_tracker.apps.users.models import User


class BloodPressureForm(forms.Form):
    """Capture systolic, diastolic, and heart rate plus optional notes."""

    systolic = forms.IntegerField(min_value=40, max_value=300)
    diastolic = forms.IntegerField(min_value=20, max_value=200)
    heart_rate = forms.IntegerField(min_value=20, max_value=250)
    notes = forms.CharField(required=False, widget=forms.Textarea)

    def clean(self) -> dict:
        """Ensure systolic is strictly greater than diastolic.

        Returns:
            The cleaned form data.

        Raises:
            forms.ValidationError: When systolic <= diastolic.
        """
        cleaned = super().clean()
        systolic = cleaned.get("systolic")
        diastolic = cleaned.get("diastolic")
        if systolic is not None and diastolic is not None and systolic <= diastolic:
            raise forms.ValidationError("Tekanan sistolik harus lebih besar dari diastolik.")
        return cleaned


class SingleValueMetricForm(forms.Form):
    """Capture a single numeric value plus optional notes.

    Used for heart rate, weight, and oxygen saturation readings.
    """

    value = forms.DecimalField(min_value=0, max_digits=6, decimal_places=1)
    notes = forms.CharField(required=False, widget=forms.Textarea)


class _DateRangeMixin:
    """Validation helper for forms with a start/end date pair."""

    def _validate_date_range(self, cleaned: dict[str, Any]) -> None:
        start = cleaned.get("start_date")
        end = cleaned.get("end_date")
        if start and end and start > end:
            raise forms.ValidationError("Tanggal mulai harus sebelum atau sama dengan tanggal akhir.")


class ActivityHistoryForm(_DateRangeMixin, forms.Form):
    """Filter and paginate the unified activity history page.

    Combines metrics, water intake, and medication-taken logs into a
    single feed. The view calls :meth:`get_page` to obtain a paginator
    page.
    """

    activity_type = forms.CharField(required=False)
    start_date = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))
    end_date = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))

    PAGE_SIZE = 20

    def __init__(self, *args: object, patient: User, **kwargs: object) -> None:
        """Initialise with the patient whose activities to filter.

        Args:
            *args: Positional args passed to :class:`forms.Form`.
            patient: The patient whose activities to filter.
            **kwargs: Keyword args passed to :class:`forms.Form`.
        """
        super().__init__(*args, **kwargs)
        self.patient = patient

    def clean(self) -> dict:
        """Validate the date range and resolve the chosen activity type."""
        cleaned = super().clean()
        self._validate_date_range(cleaned)
        return cleaned

    def _resolve_filters(self) -> tuple[list[str], list[str] | None]:
        """Return ``(kinds, metric_types)`` for the current filter state."""
        from health_tracker.apps.metrics.utils import (
            KIND_MEDICATION,
            KIND_METRIC,
            KIND_WATER,
        )

        default_kinds = [KIND_METRIC, KIND_WATER, KIND_MEDICATION]
        if not self.is_bound or not self.is_valid():
            return default_kinds, None

        raw = (self.cleaned_data.get("activity_type") or "").strip()
        if not raw:
            return default_kinds, None
        if raw == KIND_WATER:
            return [KIND_WATER], None
        if raw == KIND_MEDICATION:
            return [KIND_MEDICATION], None
        if raw.startswith(f"{KIND_METRIC}:"):
            metric_type = raw.split(":", 1)[1]
            if metric_type in dict(HealthMetric.MetricType.choices):
                return [KIND_METRIC], [metric_type]
        return default_kinds, None

    def get_activities(self) -> list:
        """Return the filtered list of ``ActivityItem`` rows."""
        from health_tracker.apps.metrics.utils import get_filtered_activities

        kinds, metric_types = self._resolve_filters()
        start = end = None
        if self.is_bound and self.is_valid():
            start = self.cleaned_data.get("start_date")
            end = self.cleaned_data.get("end_date")
        return get_filtered_activities(
            self.patient,
            kinds=kinds,
            metric_types=metric_types,
            start_date=start,
            end_date=end,
        )

    def get_page(self, page_number: str | int | None) -> Page:
        """Return the paginated ``Page`` for the filtered activity list."""
        paginator = Paginator(self.get_activities(), self.PAGE_SIZE)
        return paginator.get_page(page_number)

    @property
    def applied_filter_summary(self) -> str:
        """Return a short, human-readable description of the active filter."""
        if not self.is_bound or not self.is_valid():
            return "Semua waktu"
        start = self.cleaned_data.get("start_date")
        end = self.cleaned_data.get("end_date")
        if start and end:
            if start == end:
                return start.strftime("%-d %B %Y")
            return f"{start:%-d %b} - {end:%-d %b %Y}"
        if start:
            return f"Mulai {start:%-d %b %Y}"
        if end:
            return f"Hingga {end:%-d %b %Y}"
        return "Semua waktu"


class MetricEditForm(forms.Form):
    """Edit an existing ``HealthMetric``.

    The form exposes the same value fields as the creation forms plus
    a timestamp so caregivers can correct entries logged at the wrong
    time. Field availability depends on ``metric_type``.
    """

    timestamp = forms.DateTimeField(widget=forms.DateTimeInput(attrs={"type": "datetime-local"}))
    systolic = forms.IntegerField(min_value=50, max_value=300, required=False)
    diastolic = forms.IntegerField(min_value=30, max_value=200, required=False)
    heart_rate = forms.IntegerField(min_value=20, max_value=250, required=False)
    value = forms.DecimalField(min_value=0, max_digits=6, decimal_places=1, required=False)
    notes = forms.CharField(required=False, widget=forms.Textarea)

    def __init__(self, *args: object, metric_type: str, **kwargs: object) -> None:
        """Initialise the form scoped to ``metric_type``.

        Args:
            *args: Positional args passed to :class:`forms.Form`.
            metric_type: The ``HealthMetric.MetricType`` value being edited.
            **kwargs: Keyword args passed to :class:`forms.Form`.
        """
        super().__init__(*args, **kwargs)
        self.metric_type = metric_type
        if metric_type == HealthMetric.MetricType.BLOOD_PRESSURE:
            self.fields["systolic"].required = True
            self.fields["diastolic"].required = True
            self.fields["heart_rate"].required = True
            self.fields.pop("value", None)
        else:
            self.fields["value"].required = True
            for field_name in ("systolic", "diastolic", "heart_rate"):
                self.fields.pop(field_name, None)

    def clean(self) -> dict:
        """Validate cross-field rules for blood pressure entries."""
        cleaned = super().clean()
        if self.metric_type == HealthMetric.MetricType.BLOOD_PRESSURE:
            systolic = cleaned.get("systolic")
            diastolic = cleaned.get("diastolic")
            if systolic is not None and diastolic is not None and systolic <= diastolic:
                raise forms.ValidationError("Tekanan sistolik harus lebih besar dari diastolik.")
        return cleaned

    @classmethod
    def initial_for(cls, metric: HealthMetric) -> dict[str, Any]:
        """Return the initial form data dict for an existing metric."""
        initial: dict[str, Any] = {
            "timestamp": timezone.localtime(metric.created_at).strftime("%Y-%m-%dT%H:%M"),
            "notes": metric.notes or "",
        }
        if metric.metric_type == HealthMetric.MetricType.BLOOD_PRESSURE:
            initial.update(
                systolic=metric.value.get("systolic"),
                diastolic=metric.value.get("diastolic"),
                heart_rate=metric.value.get("heart_rate"),
            )
        else:
            initial["value"] = metric.value.get("value")
        return initial

    def apply(self, metric: HealthMetric) -> HealthMetric:
        """Persist the cleaned form data onto ``metric``."""
        from health_tracker.apps.metrics.utils import build_metric_value

        metric.value = build_metric_value(self.metric_type, self.cleaned_data)
        metric.notes = self.cleaned_data.get("notes") or ""
        metric.created_at = self.cleaned_data["timestamp"]
        metric.save()
        return metric
