"""Helpers for the data-import admin tool.

The module parses a CSV upload into unsaved model instances grouped by
target model, then persists them via ``bulk_create`` / ``bulk_update``.

The ``created_at`` two-step pattern is intentional: every importable
model uses ``auto_now_add=True``, so ``bulk_create`` overwrites the
imported timestamp with ``now()``. We restore the imported value with a
follow-up ``bulk_update``.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from django.db import transaction
from django.utils import timezone

from health_tracker.apps.hydration.models import WaterIntakeLog
from health_tracker.apps.medications.models import Medication, MedicationLog
from health_tracker.apps.metrics.models import HealthMetric
from health_tracker.apps.users.models import User

ACTIVITY_BP: str = HealthMetric.MetricType.BLOOD_PRESSURE
ACTIVITY_HR: str = HealthMetric.MetricType.HEART_RATE
ACTIVITY_WT: str = HealthMetric.MetricType.WEIGHT
ACTIVITY_OS: str = HealthMetric.MetricType.OXYGEN_SATURATION
ACTIVITY_WATER: str = "water"
ACTIVITY_MEDICATION: str = "medication"

ACTIVITY_CHOICES: tuple[tuple[str, str], ...] = (
    (ACTIVITY_BP, "Blood Pressure"),
    (ACTIVITY_HR, "Heart Rate"),
    (ACTIVITY_WT, "Weight"),
    (ACTIVITY_OS, "Oxygen Saturation"),
    (ACTIVITY_WATER, "Water Intake"),
    (ACTIVITY_MEDICATION, "Medication Taken"),
)

REQUIRED_HEADERS: tuple[str, ...] = ("activity_type", "created_at")

CSV_COLUMNS: tuple[str, ...] = (
    "activity_type",
    "created_at",
    "systolic",
    "diastolic",
    "heart_rate",
    "weight_kg",
    "spo2",
    "volume_ml",
    "medication_id",
    "notes",
)

MAX_UPLOAD_BYTES: int = 5 * 1024 * 1024


@dataclass
class RowError:
    """A validation error encountered while parsing a CSV row.

    Attributes:
        line: 1-based CSV line number (header is line 1).
        message: Human-readable error description.
    """

    line: int
    message: str


@dataclass
class ParsedRows:
    """Unsaved model instances grouped by target model.

    Each instance has its desired ``created_at`` already assigned, but
    will be overwritten on insert by ``auto_now_add`` and restored via
    :func:`_restore_timestamps` after ``bulk_create``.
    """

    metrics: list[HealthMetric] = field(default_factory=list)
    waters: list[WaterIntakeLog] = field(default_factory=list)
    medication_logs: list[MedicationLog] = field(default_factory=list)

    @property
    def total(self) -> int:
        """Return the total number of rows across all groups."""
        return len(self.metrics) + len(self.waters) + len(self.medication_logs)


@dataclass
class ImportResult:
    """Outcome of an import run.

    Attributes:
        metric_count: Number of ``HealthMetric`` rows created.
        water_count: Number of ``WaterIntakeLog`` rows created.
        medication_log_count: Number of ``MedicationLog`` rows created.
        errors: Per-row validation errors. When non-empty, the import is
            aborted and no rows are persisted.
    """

    metric_count: int = 0
    water_count: int = 0
    medication_log_count: int = 0
    errors: list[RowError] = field(default_factory=list)

    @property
    def success(self) -> bool:
        """Return ``True`` when the import committed without errors."""
        return not self.errors

    @property
    def total_created(self) -> int:
        """Return the total number of records created."""
        return self.metric_count + self.water_count + self.medication_log_count


def parse_datetime(raw: str) -> datetime:
    """Parse a CSV ``created_at`` cell into a timezone-aware datetime.

    Accepts ISO 8601-ish forms with or without seconds, with ``T`` or
    space separator, and date-only values (midnight is assumed). Naive
    inputs are interpreted in the project's current timezone.

    Args:
        raw: The raw cell value.

    Returns:
        A timezone-aware datetime.

    Raises:
        ValueError: When ``raw`` does not match any accepted form.
    """
    value = raw.strip()
    if not value:
        raise ValueError("created_at is required")
    candidates = (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M",
        "%Y-%m-%d",
    )
    for fmt in candidates:
        try:
            parsed = datetime.strptime(value, fmt)
        except ValueError:
            continue
        if timezone.is_naive(parsed):
            return timezone.make_aware(parsed, timezone.get_current_timezone())
        return parsed
    raise ValueError(f"could not parse datetime: {raw!r}")


def _require(row: dict[str, str], column: str) -> str:
    """Return the stripped value for ``column`` or raise ``ValueError``."""
    raw = (row.get(column) or "").strip()
    if not raw:
        raise ValueError(f"{column} is required for this activity_type")
    return raw


def _optional_int(row: dict[str, str], column: str) -> int | None:
    """Return ``int(row[column])`` or ``None`` if blank."""
    raw = (row.get(column) or "").strip()
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"{column} must be an integer, got {raw!r}") from exc


def _require_int(row: dict[str, str], column: str) -> int:
    """Return ``int(row[column])`` or raise ``ValueError`` if blank/invalid."""
    raw = _require(row, column)
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"{column} must be an integer, got {raw!r}") from exc


def _require_decimal(row: dict[str, str], column: str) -> Decimal:
    """Return ``Decimal(row[column])`` or raise ``ValueError`` if blank/invalid."""
    raw = _require(row, column)
    try:
        return Decimal(raw)
    except InvalidOperation as exc:
        raise ValueError(f"{column} must be a number, got {raw!r}") from exc


def _build_metric(
    row: dict[str, str],
    patient: User,
    activity_type: str,
    created_at: datetime,
) -> HealthMetric:
    """Construct an unsaved ``HealthMetric`` from a CSV row."""
    notes = (row.get("notes") or "").strip()
    if activity_type == ACTIVITY_BP:
        systolic = _require_int(row, "systolic")
        diastolic = _require_int(row, "diastolic")
        if systolic <= diastolic:
            raise ValueError("systolic must be greater than diastolic")
        value: dict[str, Any] = {"systolic": systolic, "diastolic": diastolic}
        heart_rate = _optional_int(row, "heart_rate")
        if heart_rate is not None:
            value["heart_rate"] = heart_rate
    elif activity_type == ACTIVITY_HR:
        value = {"value": _require_int(row, "heart_rate")}
    elif activity_type == ACTIVITY_WT:
        value = {"value": float(_require_decimal(row, "weight_kg"))}
    elif activity_type == ACTIVITY_OS:
        value = {"value": _require_int(row, "spo2")}
    else:
        raise ValueError(f"unhandled metric activity_type: {activity_type!r}")
    return HealthMetric(
        patient=patient,
        metric_type=activity_type,
        value=value,
        notes=notes,
        created_at=created_at,
    )


def _build_water(row: dict[str, str], patient: User, created_at: datetime) -> WaterIntakeLog:
    """Construct an unsaved ``WaterIntakeLog`` from a CSV row."""
    volume_ml = _require_int(row, "volume_ml")
    if volume_ml <= 0:
        raise ValueError("volume_ml must be positive")
    notes = (row.get("notes") or "").strip()
    return WaterIntakeLog(
        patient=patient,
        volume_ml=volume_ml,
        notes=notes,
        created_at=created_at,
    )


def _build_medication_log(
    row: dict[str, str],
    medications_by_id: dict[int, Medication],
    created_at: datetime,
) -> MedicationLog:
    """Construct an unsaved ``MedicationLog`` from a CSV row."""
    medication_id = _require_int(row, "medication_id")
    medication = medications_by_id.get(medication_id)
    if medication is None:
        raise ValueError(
            f"medication_id {medication_id} does not exist or does not belong to the selected patient"
        )
    return MedicationLog(medication=medication, taken_at=created_at)


def parse_csv(file_bytes: bytes, patient: User) -> tuple[ParsedRows, list[RowError]]:
    """Parse and validate a CSV payload for ``patient``.

    Args:
        file_bytes: Raw CSV file contents (UTF-8 encoded).
        patient: The patient who will own the imported records.

    Returns:
        A tuple of ``(parsed_rows, errors)``. When ``errors`` is
        non-empty the caller MUST abort the import.
    """
    errors: list[RowError] = []
    parsed = ParsedRows()

    try:
        text = file_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        errors.append(RowError(line=1, message="File must be UTF-8 encoded CSV."))
        return parsed, errors

    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        errors.append(RowError(line=1, message="CSV is empty."))
        return parsed, errors

    missing = [column for column in REQUIRED_HEADERS if column not in reader.fieldnames]
    if missing:
        errors.append(
            RowError(line=1, message=f"Missing required column(s): {', '.join(missing)}")
        )
        return parsed, errors

    medications_by_id: dict[int, Medication] = {
        medication.pk: medication for medication in Medication.objects.filter(patient=patient)
    }

    valid_metric_types = {ACTIVITY_BP, ACTIVITY_HR, ACTIVITY_WT, ACTIVITY_OS}

    for row_index, row in enumerate(reader, start=2):
        activity_type = (row.get("activity_type") or "").strip()
        if not activity_type:
            errors.append(RowError(line=row_index, message="activity_type is required."))
            continue
        try:
            created_at = parse_datetime(row.get("created_at") or "")
        except ValueError as exc:
            errors.append(RowError(line=row_index, message=str(exc)))
            continue
        try:
            if activity_type in valid_metric_types:
                parsed.metrics.append(_build_metric(row, patient, activity_type, created_at))
            elif activity_type == ACTIVITY_WATER:
                parsed.waters.append(_build_water(row, patient, created_at))
            elif activity_type == ACTIVITY_MEDICATION:
                parsed.medication_logs.append(
                    _build_medication_log(row, medications_by_id, created_at)
                )
            else:
                errors.append(
                    RowError(
                        line=row_index,
                        message=f"unknown activity_type: {activity_type!r}",
                    )
                )
        except ValueError as exc:
            errors.append(RowError(line=row_index, message=str(exc)))

    return parsed, errors


def _restore_timestamps(
    model: type,
    instances: list,
    timestamp_field: str,
    desired_timestamps: list[datetime],
) -> None:
    """Restore imported timestamps overwritten by ``auto_now_add``.

    ``bulk_create`` runs the field's ``pre_save`` which forces
    ``auto_now_add`` timestamps to ``now()``. We reset them to the
    imported values in one batch ``UPDATE``.
    """
    for instance, desired in zip(instances, desired_timestamps):
        setattr(instance, timestamp_field, desired)
    model.objects.bulk_update(instances, [timestamp_field])


@transaction.atomic
def persist(parsed: ParsedRows) -> tuple[int, int, int]:
    """Insert all parsed rows and return per-type created counts.

    Returns:
        A tuple ``(metric_count, water_count, medication_log_count)``.
    """
    metric_count = water_count = medication_log_count = 0

    if parsed.metrics:
        desired = [instance.created_at for instance in parsed.metrics]
        HealthMetric.objects.bulk_create(parsed.metrics)
        _restore_timestamps(HealthMetric, parsed.metrics, "created_at", desired)
        metric_count = len(parsed.metrics)

    if parsed.waters:
        desired = [instance.created_at for instance in parsed.waters]
        WaterIntakeLog.objects.bulk_create(parsed.waters)
        _restore_timestamps(WaterIntakeLog, parsed.waters, "created_at", desired)
        water_count = len(parsed.waters)

    if parsed.medication_logs:
        desired = [instance.taken_at for instance in parsed.medication_logs]
        MedicationLog.objects.bulk_create(parsed.medication_logs)
        _restore_timestamps(MedicationLog, parsed.medication_logs, "taken_at", desired)
        medication_log_count = len(parsed.medication_logs)

    return metric_count, water_count, medication_log_count
