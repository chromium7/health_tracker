"""Hydration tracking models."""

from __future__ import annotations

from django.db import models

from health_tracker.apps.users.models import User


class WaterIntakeLog(models.Model):
    """A single water-intake event for a patient.

    Attributes:
        patient: The patient who consumed the water.
        volume_ml: Volume consumed in this event, in millilitres.
        created_at: Timestamp set automatically on creation.
    """

    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name="water_logs")
    volume_ml = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.volume_ml}ml for {self.patient.username} at {self.created_at:%H:%M}"
