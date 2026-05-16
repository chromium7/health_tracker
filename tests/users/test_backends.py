"""Tests for the PIN authentication backend."""

from __future__ import annotations

from django.test import TestCase

from health_tracker.apps.users.backends import PINAuthBackend
from health_tracker.apps.users.models import User


class PINAuthBackendTests(TestCase):
    """Behavioural tests for :class:`PINAuthBackend`."""

    def setUp(self) -> None:
        self.backend = PINAuthBackend()
        self.user = User.objects.create(
            username="alice",
            pin="1234",
            role=User.Role.PATIENT,
        )

    def test_authenticate_returns_user_on_match(self) -> None:
        result = self.backend.authenticate(None, username="alice", pin="1234")
        self.assertEqual(result, self.user)

    def test_authenticate_returns_none_on_wrong_pin(self) -> None:
        result = self.backend.authenticate(None, username="alice", pin="9999")
        self.assertIsNone(result)

    def test_authenticate_returns_none_on_unknown_user(self) -> None:
        result = self.backend.authenticate(None, username="bob", pin="1234")
        self.assertIsNone(result)

    def test_authenticate_returns_none_when_inactive(self) -> None:
        self.user.is_active = False
        self.user.save()
        result = self.backend.authenticate(None, username="alice", pin="1234")
        self.assertIsNone(result)

    def test_authenticate_returns_none_on_missing_input(self) -> None:
        self.assertIsNone(self.backend.authenticate(None, username="", pin="1234"))
        self.assertIsNone(self.backend.authenticate(None, username="alice", pin=""))
        self.assertIsNone(self.backend.authenticate(None, username=None, pin=None))

    def test_get_user_returns_user(self) -> None:
        self.assertEqual(self.backend.get_user(self.user.pk), self.user)

    def test_get_user_returns_none_when_missing(self) -> None:
        self.assertIsNone(self.backend.get_user(999_999))


class GetPatientTests(TestCase):
    """Tests for the ``User.get_patient`` helper."""

    def test_patient_returns_self(self) -> None:
        patient = User.objects.create(
            username="pat",
            pin="0000",
            role=User.Role.PATIENT,
        )
        self.assertEqual(patient.get_patient(), patient)

    def test_caregiver_returns_patient_profile(self) -> None:
        patient = User.objects.create(
            username="pat",
            pin="0000",
            role=User.Role.PATIENT,
        )
        caregiver = User.objects.create(
            username="care",
            pin="1111",
            role=User.Role.CAREGIVER,
            patient_profile=patient,
        )
        self.assertEqual(caregiver.get_patient(), patient)

    def test_caregiver_without_patient_raises(self) -> None:
        caregiver = User.objects.create(
            username="care",
            pin="1111",
            role=User.Role.CAREGIVER,
        )
        with self.assertRaises(ValueError):
            caregiver.get_patient()
