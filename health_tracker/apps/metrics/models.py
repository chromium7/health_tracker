"""HealthMetric model: a single health reading owned by a patient."""

from __future__ import annotations

from django.db import models

from health_tracker.apps.users.models import User


class HealthMetric(models.Model):
    """A single health reading logged by or for a patient.

    The ``value`` JSON column stores a different shape per
    ``metric_type``:

    - ``'bp'``: ``{"systolic": int, "diastolic": int, "heart_rate": int}``
    - ``'hr'``: ``{"value": int}``
    - ``'wt'``: ``{"value": float}`` (kilograms)
    - ``'os'``: ``{"value": int}`` (percentage)

    Older blood-pressure records may lack ``heart_rate``; the display
    helper treats that key as optional.

    Attributes:
        patient: The patient this reading belongs to.
        metric_type: One of the ``METRIC_*`` constants.
        value: JSON payload; structure varies by ``metric_type``.
        notes: Optional free-text note from the logger.
        created_at: Timestamp set automatically on creation.
    """

    class MetricType(models.TextChoices):
        """The kinds of readings ``HealthMetric`` rows can represent."""

        BLOOD_PRESSURE = "bp", "Blood Pressure"
        HEART_RATE = "hr", "Heart Rate"
        WEIGHT = "wt", "Weight"
        OXYGEN_SATURATION = "os", "Oxygen Saturation"

    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name="metrics")
    metric_type = models.CharField(max_length=2, choices=MetricType.choices)
    value = models.JSONField()
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def display_value(self) -> str:
        """Render the JSON payload as a short human-readable string."""
        if self.metric_type == self.MetricType.BLOOD_PRESSURE:
            base = f"{self.value['systolic']}/{self.value['diastolic']} mmHg"
            heart_rate = self.value.get("heart_rate")
            if heart_rate:
                return f"{base} · {heart_rate} bpm"
            return base
        if self.metric_type == self.MetricType.HEART_RATE:
            return f"{self.value['value']} bpm"
        if self.metric_type == self.MetricType.WEIGHT:
            return f"{self.value['value']} kg"
        if self.metric_type == self.MetricType.OXYGEN_SATURATION:
            return f"{self.value['value']}%"
        return ""

    def __str__(self) -> str:
        return f"{self.get_metric_type_display()} for {self.patient.username} on {self.created_at:%Y-%m-%d}"
