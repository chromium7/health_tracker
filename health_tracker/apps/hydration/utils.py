"""Helpers and constants for the hydration app."""

from __future__ import annotations

from django.db.models import QuerySet, Sum
from django.utils import timezone

from health_tracker.apps.hydration.models import WaterIntakeLog
from health_tracker.apps.users.models import User

DAILY_TARGET_ML: int = 2000

MIN_VOLUME_ML: int = 1
MAX_VOLUME_ML: int = 2000


def get_today_total_ml(patient: User) -> int:
    """Return today's total water intake in millilitres for ``patient``.

    Args:
        patient: The patient whose intake to aggregate.

    Returns:
        The sum of ``volume_ml`` across all of today's logs, or ``0``
        if no logs exist for today.
    """
    today = timezone.localdate()
    total = WaterIntakeLog.objects.filter(
        patient=patient,
        created_at__date=today,
    ).aggregate(total=Sum("volume_ml"))["total"]
    return total or 0


def get_today_water_logs(patient: User) -> QuerySet[WaterIntakeLog]:
    """Return today's water-intake events for ``patient``, newest first.

    Args:
        patient: The patient whose logs to return.

    Returns:
        A queryset of today's ``WaterIntakeLog`` rows.
    """
    today = timezone.localdate()
    return WaterIntakeLog.objects.filter(
        patient=patient,
        created_at__date=today,
    )
