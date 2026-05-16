"""Medication and MedicationLog models."""

from __future__ import annotations

from django.db import models

from health_tracker.apps.users.models import User


class Medication(models.Model):
    """A prescribed medication belonging to a patient.

    Attributes:
        patient: The patient this medication is prescribed for.
        name: Medication name.
        dosage: Dosage description (e.g. ``"10mg once daily"``).
        prescribed_by: Name of the prescribing doctor.
        reason: Clinical reason for the prescription.
        is_active: ``False`` when the medication has been stopped (course
            finished, side effects, ran out, doctor stopped it, etc.).
        stopped_at: The date the medication was stopped. ``None`` while active.
        stop_reason: Short code describing why it was stopped. Blank while active.
    """

    class StopReason(models.TextChoices):
        FINISHED = "finished", "Selesai kursus"
        SYMPTOMS = "symptoms", "Efek samping"
        OUT = "out", "Habis"
        DOCTOR = "doctor", "Dihentikan dokter"
        OTHER = "other", "Lainnya"

    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name="medications")
    name = models.CharField(max_length=100)
    dosage = models.CharField(max_length=50, blank=True)
    prescribed_by = models.CharField(max_length=100, blank=True)
    reason = models.CharField(max_length=200, blank=True)
    is_active = models.BooleanField(default=True)
    stopped_at = models.DateField(null=True, blank=True)
    stop_reason = models.CharField(max_length=20, blank=True, choices=StopReason.choices)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.dosage})"


class MedicationLog(models.Model):
    """A record of a single 'medication taken' event.

    Attributes:
        medication: The medication that was taken.
        taken_at: Timestamp set automatically on creation.
    """

    medication = models.ForeignKey(
        Medication,
        on_delete=models.CASCADE,
        related_name="logs",
    )
    taken_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-taken_at"]

    def __str__(self) -> str:
        return f"{self.medication.name} taken at {self.taken_at:%Y-%m-%d %H:%M}"
