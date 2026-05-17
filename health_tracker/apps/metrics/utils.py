"""Helpers for the metrics app: queryset builders, activity feed, form dispatch."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Iterable

from django import forms
from django.urls import reverse

from health_tracker.apps.hydration.models import WaterIntakeLog
from health_tracker.apps.medications.models import MedicationLog
from health_tracker.apps.metrics.forms import BloodPressureForm, SingleValueMetricForm
from health_tracker.apps.metrics.models import HealthMetric
from health_tracker.apps.users.models import User

METRIC_FORM_MAP: dict[str, type[forms.Form]] = {
    HealthMetric.MetricType.BLOOD_PRESSURE: BloodPressureForm,
    HealthMetric.MetricType.HEART_RATE: SingleValueMetricForm,
    HealthMetric.MetricType.WEIGHT: SingleValueMetricForm,
    HealthMetric.MetricType.OXYGEN_SATURATION: SingleValueMetricForm,
}

METRIC_PAGE_TITLES: dict[str, str] = {
    HealthMetric.MetricType.BLOOD_PRESSURE: "Catat Tekanan Darah",
    HealthMetric.MetricType.HEART_RATE: "Catat Detak Jantung",
    HealthMetric.MetricType.WEIGHT: "Catat Berat Badan",
    HealthMetric.MetricType.OXYGEN_SATURATION: "Catat Saturasi Oksigen",
}

METRIC_LABELS_ID: dict[str, str] = {
    HealthMetric.MetricType.BLOOD_PRESSURE: "Tekanan Darah",
    HealthMetric.MetricType.HEART_RATE: "Detak Jantung",
    HealthMetric.MetricType.WEIGHT: "Berat Badan",
    HealthMetric.MetricType.OXYGEN_SATURATION: "Saturasi Oksigen",
}

KIND_METRIC: str = "metric"
KIND_WATER: str = "water"
KIND_MEDICATION: str = "medication"

ACTIVITY_TYPE_CHOICES: list[tuple[str, str]] = [
    ("", "Semua aktivitas"),
    (f"{KIND_METRIC}:{HealthMetric.MetricType.BLOOD_PRESSURE}", "Tekanan Darah"),
    (f"{KIND_METRIC}:{HealthMetric.MetricType.HEART_RATE}", "Detak Jantung"),
    (f"{KIND_METRIC}:{HealthMetric.MetricType.WEIGHT}", "Berat Badan"),
    (f"{KIND_METRIC}:{HealthMetric.MetricType.OXYGEN_SATURATION}", "Saturasi Oksigen"),
    (KIND_WATER, "Konsumsi Air"),
    (KIND_MEDICATION, "Obat"),
]


@dataclass(frozen=True)
class ActivityItem:
    """A single row in the unified activity feed.

    Attributes:
        kind: ``"metric"``, ``"water"``, or ``"medication"``.
        metric_type: For metric rows, the ``HealthMetric.MetricType`` value.
        object_id: Primary key of the underlying record.
        label: Short Indonesian label (e.g. ``"Tekanan Darah"``).
        value_display: Pre-formatted value string.
        timestamp: When the activity occurred.
        detail_url: URL of the detail page for this record.
        icon: Icon key used by ``_icons.html``.
        icon_modifier: BEM modifier suffix for tinted icon backgrounds.
    """

    kind: str
    metric_type: str | None
    object_id: int
    label: str
    value_display: str
    timestamp: datetime
    detail_url: str
    icon: str
    icon_modifier: str


def build_metric_value(metric_type: str, cleaned_data: dict[str, Any]) -> dict[str, Any]:
    """Construct the JSON ``value`` payload for a new ``HealthMetric``.

    Args:
        metric_type: One of the ``HealthMetric.METRIC_*`` constants.
        cleaned_data: The form's ``cleaned_data`` mapping.

    Returns:
        A dict in the schema required for the given metric type.

    Raises:
        ValueError: If ``metric_type`` is not a recognised type.

    Examples:
        >>> build_metric_value('bp', {'systolic': 120, 'diastolic': 80})
        {'systolic': 120, 'diastolic': 80}
        >>> build_metric_value('hr', {'value': Decimal('72')})
        {'value': 72}
    """
    if metric_type == HealthMetric.MetricType.BLOOD_PRESSURE:
        return {
            "systolic": int(cleaned_data["systolic"]),
            "diastolic": int(cleaned_data["diastolic"]),
            "heart_rate": int(cleaned_data["heart_rate"]),
        }
    if metric_type == HealthMetric.MetricType.HEART_RATE:
        return {"value": int(_to_decimal(cleaned_data["value"]))}
    if metric_type == HealthMetric.MetricType.WEIGHT:
        return {"value": float(_to_decimal(cleaned_data["value"]))}
    if metric_type == HealthMetric.MetricType.OXYGEN_SATURATION:
        return {"value": int(_to_decimal(cleaned_data["value"]))}
    raise ValueError(f"Unrecognised metric_type: {metric_type!r}")


def _to_decimal(raw: Any) -> Decimal:
    """Coerce a numeric form value to ``Decimal``."""
    if isinstance(raw, Decimal):
        return raw
    return Decimal(str(raw))


def get_latest_metrics(patient: User) -> dict[str, HealthMetric | None]:
    """Return the most recent reading for each metric type for ``patient``.

    Args:
        patient: The patient whose readings to inspect.

    Returns:
        A dict keyed by metric type with the latest ``HealthMetric``
        instance or ``None`` if no reading of that type exists.
    """
    latest: dict[str, HealthMetric | None] = {metric_type: None for metric_type, _ in HealthMetric.MetricType.choices}
    queryset = (
        HealthMetric.objects.filter(patient=patient).select_related("patient").order_by("metric_type", "-created_at")
    )
    seen: set[str] = set()
    for metric in queryset:
        if metric.metric_type in seen:
            continue
        latest[metric.metric_type] = metric
        seen.add(metric.metric_type)
        if len(seen) == len(latest):
            break
    return latest


def get_metric_cards(patient: User) -> list[dict[str, Any]]:
    """Build the dashboard reading cards for ``patient``.

    Returns:
        A list of one card per metric type, each containing the type
        key, its display label, and the latest ``HealthMetric`` or
        ``None``.
    """
    latest = get_latest_metrics(patient)
    return [
        {
            "metric_type": metric_type,
            "label": label,
            "latest": latest[metric_type],
        }
        for metric_type, label in HealthMetric.MetricType.choices
    ]


def _metric_to_activity(metric: HealthMetric) -> ActivityItem:
    """Convert a ``HealthMetric`` row to an ``ActivityItem``."""
    icon = (
        "user"
        if metric.metric_type == HealthMetric.MetricType.WEIGHT
        else ("drop" if metric.metric_type == HealthMetric.MetricType.OXYGEN_SATURATION else "heart")
    )
    return ActivityItem(
        kind=KIND_METRIC,
        metric_type=metric.metric_type,
        object_id=metric.pk,
        label=METRIC_LABELS_ID[metric.metric_type],
        value_display=metric.display_value,
        timestamp=metric.created_at,
        detail_url=reverse("metric_detail", kwargs={"pk": metric.pk}),
        icon=icon,
        icon_modifier=metric.metric_type,
    )


def _water_to_activity(log: WaterIntakeLog) -> ActivityItem:
    """Convert a ``WaterIntakeLog`` row to an ``ActivityItem``."""
    return ActivityItem(
        kind=KIND_WATER,
        metric_type=None,
        object_id=log.pk,
        label="Minum",
        value_display=f"{log.volume_ml} ml",
        timestamp=log.created_at,
        detail_url=reverse("drink_detail", kwargs={"pk": log.pk}),
        icon="drop",
        icon_modifier="water",
    )


def _medication_to_activity(log: MedicationLog) -> ActivityItem:
    """Convert a ``MedicationLog`` row to an ``ActivityItem``."""
    medication = log.medication
    dosage = f" - {medication.dosage}" if medication.dosage else ""
    return ActivityItem(
        kind=KIND_MEDICATION,
        metric_type=None,
        object_id=log.pk,
        label="Obat",
        value_display=f"{medication.name}{dosage}",
        timestamp=log.taken_at,
        detail_url=reverse("medication_log_detail", kwargs={"pk": log.pk}),
        icon="pill",
        icon_modifier="meds",
    )


def _collect_activities(
    patient: User,
    *,
    kinds: Iterable[str],
    metric_types: Iterable[str] | None = None,
    start_date: Any | None = None,
    end_date: Any | None = None,
) -> list[ActivityItem]:
    """Build the combined activity list filtered by ``kinds`` and date range."""
    items: list[ActivityItem] = []

    if KIND_METRIC in kinds:
        metrics = HealthMetric.objects.filter(patient=patient).select_related("patient")
        if metric_types:
            metrics = metrics.filter(metric_type__in=list(metric_types))
        if start_date:
            metrics = metrics.filter(created_at__date__gte=start_date)
        if end_date:
            metrics = metrics.filter(created_at__date__lte=end_date)
        items.extend(_metric_to_activity(metric) for metric in metrics)

    if KIND_WATER in kinds:
        drinks = WaterIntakeLog.objects.filter(patient=patient).select_related("patient")
        if start_date:
            drinks = drinks.filter(created_at__date__gte=start_date)
        if end_date:
            drinks = drinks.filter(created_at__date__lte=end_date)
        items.extend(_water_to_activity(drink) for drink in drinks)

    if KIND_MEDICATION in kinds:
        logs = MedicationLog.objects.filter(medication__patient=patient).select_related("medication__patient")
        if start_date:
            logs = logs.filter(taken_at__date__gte=start_date)
        if end_date:
            logs = logs.filter(taken_at__date__lte=end_date)
        items.extend(_medication_to_activity(log) for log in logs)

    items.sort(key=lambda item: item.timestamp, reverse=True)
    return items


def get_recent_activities(patient: User, limit: int = 5) -> list[ActivityItem]:
    """Return the patient's most recent activities across all data types.

    Args:
        patient: The patient whose activities to fetch.
        limit: Maximum number of rows to return.

    Returns:
        A list of ``ActivityItem`` rows ordered newest first.
    """
    items = _collect_activities(
        patient,
        kinds=(KIND_METRIC, KIND_WATER, KIND_MEDICATION),
    )
    return items[:limit]


def get_filtered_activities(
    patient: User,
    *,
    kinds: Iterable[str],
    metric_types: Iterable[str] | None = None,
    start_date: Any | None = None,
    end_date: Any | None = None,
) -> list[ActivityItem]:
    """Return ``ActivityItem`` rows matching the supplied filters."""
    return _collect_activities(
        patient,
        kinds=kinds,
        metric_types=metric_types,
        start_date=start_date,
        end_date=end_date,
    )
