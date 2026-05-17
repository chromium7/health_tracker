"""Tests for the hydration utility helpers."""

from __future__ import annotations

from django.test import TestCase

from health_tracker.apps.hydration.models import WaterIntakeLog
from health_tracker.apps.hydration.utils import (
    MAX_VOLUME_ML,
    MIN_VOLUME_ML,
    get_today_total_ml,
)
from health_tracker.apps.users.models import User


class VolumeBoundsTests(TestCase):
    """Sanity checks for the volume bounds and per-patient daily target."""

    def test_bounds_are_positive(self) -> None:
        self.assertGreater(MIN_VOLUME_ML, 0)
        self.assertGreater(MAX_VOLUME_ML, MIN_VOLUME_ML)

    def test_default_daily_target_is_750ml(self) -> None:
        patient = User.objects.create(
            username="default_pat",
            pin="0000",
            role=User.Role.PATIENT,
        )
        self.assertEqual(patient.daily_water_target_ml, 750)


class GetTodayTotalMlTests(TestCase):
    """Tests for :func:`get_today_total_ml`."""

    def setUp(self) -> None:
        self.patient = User.objects.create(
            username="pat",
            pin="0000",
            role=User.Role.PATIENT,
        )

    def test_returns_zero_when_no_logs(self) -> None:
        self.assertEqual(get_today_total_ml(self.patient), 0)

    def test_sums_today_volumes(self) -> None:
        WaterIntakeLog.objects.create(patient=self.patient, volume_ml=250)
        WaterIntakeLog.objects.create(patient=self.patient, volume_ml=500)
        self.assertEqual(get_today_total_ml(self.patient), 750)

    def test_excludes_other_patient_logs(self) -> None:
        other = User.objects.create(
            username="other",
            pin="0000",
            role=User.Role.PATIENT,
        )
        WaterIntakeLog.objects.create(patient=other, volume_ml=500)
        self.assertEqual(get_today_total_ml(self.patient), 0)
