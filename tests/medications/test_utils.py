"""Tests for the medications utility helpers."""

from __future__ import annotations

from django.test import TestCase

from health_tracker.apps.medications.models import Medication, MedicationLog
from health_tracker.apps.medications.utils import (
    get_active_medications,
    get_today_taken_ids,
)
from health_tracker.apps.users.models import User


class GetActiveMedicationsTests(TestCase):
    """Tests for :func:`get_active_medications`."""

    def setUp(self) -> None:
        self.patient = User.objects.create(
            username="pat",
            pin="0000",
            role=User.Role.PATIENT,
        )

    def test_returns_only_active_medications(self) -> None:
        active = Medication.objects.create(
            patient=self.patient,
            name="Aspirin",
            is_active=True,
        )
        Medication.objects.create(
            patient=self.patient,
            name="Old drug",
            is_active=False,
        )
        result = list(get_active_medications(self.patient))
        self.assertEqual(result, [active])

    def test_filters_by_patient(self) -> None:
        other = User.objects.create(
            username="other",
            pin="0000",
            role=User.Role.PATIENT,
        )
        Medication.objects.create(patient=other, name="Not mine")
        result = list(get_active_medications(self.patient))
        self.assertEqual(result, [])


class GetTodayTakenIdsTests(TestCase):
    """Tests for :func:`get_today_taken_ids`."""

    def setUp(self) -> None:
        self.patient = User.objects.create(
            username="pat",
            pin="0000",
            role=User.Role.PATIENT,
        )
        self.med = Medication.objects.create(
            patient=self.patient,
            name="Aspirin",
        )

    def test_empty_when_no_logs(self) -> None:
        self.assertEqual(get_today_taken_ids(self.patient), set())

    def test_includes_today_logs(self) -> None:
        MedicationLog.objects.create(medication=self.med)
        self.assertEqual(get_today_taken_ids(self.patient), {self.med.pk})

    def test_excludes_other_patient_logs(self) -> None:
        other_patient = User.objects.create(
            username="other",
            pin="0000",
            role=User.Role.PATIENT,
        )
        other_med = Medication.objects.create(
            patient=other_patient,
            name="Not mine",
        )
        MedicationLog.objects.create(medication=other_med)
        self.assertEqual(get_today_taken_ids(self.patient), set())
