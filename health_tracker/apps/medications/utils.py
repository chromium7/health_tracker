"""Query helpers for the medications app."""

from __future__ import annotations

from dataclasses import dataclass

from django.db.models import QuerySet
from django.utils import timezone

from health_tracker.apps.medications.models import Medication, MedicationLog
from health_tracker.apps.users.models import User


@dataclass(frozen=True)
class MedicationProgress:
    """Aggregate 'medications taken today' snapshot for the dashboard.

    Attributes:
        taken: Number of active medications with a log today.
        total: Total number of active medications.
    """

    taken: int
    total: int

    @property
    def remaining(self) -> int:
        """Return the number of doses still due today."""
        return max(self.total - self.taken, 0)


@dataclass(frozen=True)
class MedicationCard:
    """A medication row pre-shaped for the medications page.

    Attributes:
        medication: The underlying ``Medication`` instance.
        taken: Whether it has been logged today.
        taken_at: The most recent log timestamp for today, or ``None``.
    """

    medication: Medication
    taken: bool
    taken_at: object | None


def get_active_medications(patient: User) -> QuerySet[Medication]:
    """Return the active medications prescribed to ``patient``.

    Args:
        patient: The patient whose medications to return.

    Returns:
        A queryset of active ``Medication`` rows ordered by name.
    """
    return Medication.objects.filter(patient=patient, is_active=True)


def get_stopped_medications(patient: User) -> QuerySet[Medication]:
    """Return ``patient``'s stopped medications, most recently stopped first."""
    return Medication.objects.filter(patient=patient, is_active=False).order_by(
        "-stopped_at",
        "name",
    )


def get_today_taken_ids(patient: User) -> set[int]:
    """Return the PKs of medications already marked taken today.

    Uses ``taken_at__date == today`` in the patient's local timezone.
    Returned as a ``set`` for O(1) membership checks in templates.

    Args:
        patient: The patient whose logs to inspect.

    Returns:
        A set of ``Medication`` primary keys.
    """
    today = timezone.localdate()
    return set(
        MedicationLog.objects.filter(
            medication__patient=patient,
            taken_at__date=today,
        ).values_list("medication_id", flat=True)
    )


def get_today_taken_at(patient: User) -> dict[int, object]:
    """Return the latest 'taken at' timestamp per medication, for today.

    Args:
        patient: The patient whose logs to inspect.

    Returns:
        A mapping of ``Medication`` PK to the latest ``taken_at``
        ``datetime`` recorded today. Medications without a log today
        are absent from the mapping.
    """
    today = timezone.localdate()
    logs = MedicationLog.objects.filter(
        medication__patient=patient,
        taken_at__date=today,
    ).order_by("medication_id", "-taken_at")
    latest: dict[int, object] = {}
    for log in logs:
        latest.setdefault(log.medication_id, log.taken_at)
    return latest


def get_medication_progress(patient: User) -> MedicationProgress:
    """Return the 'X of Y taken today' summary for the dashboard.

    Args:
        patient: The patient to summarise.

    Returns:
        A ``MedicationProgress`` snapshot.
    """
    active_ids = set(get_active_medications(patient).values_list("pk", flat=True))
    taken_ids = get_today_taken_ids(patient)
    taken_today_active = active_ids & taken_ids
    return MedicationProgress(taken=len(taken_today_active), total=len(active_ids))


def get_medication_cards(patient: User) -> list[MedicationCard]:
    """Return per-medication cards for the medications page.

    Each card includes whether the medication has been logged today and,
    if so, the latest ``taken_at`` timestamp.

    Args:
        patient: The patient to render cards for.

    Returns:
        A list of ``MedicationCard`` entries ordered by medication name.
    """
    active = list(get_active_medications(patient))
    taken_at = get_today_taken_at(patient)
    return [
        MedicationCard(
            medication=med,
            taken=med.pk in taken_at,
            taken_at=taken_at.get(med.pk),
        )
        for med in active
    ]
