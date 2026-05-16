"""Tests for the medications views."""

from __future__ import annotations

from datetime import timedelta

from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from health_tracker.apps.medications.models import Medication, MedicationLog
from health_tracker.apps.users.models import User


class MedicationListViewTests(TestCase):
    """Tests for :func:`medication_list_view`."""

    def setUp(self) -> None:
        self.client = Client()
        self.patient = User.objects.create(
            username="pat",
            pin="0000",
            role=User.Role.PATIENT,
        )
        self.med = Medication.objects.create(
            patient=self.patient,
            name="Aspirin",
            dosage="10mg",
        )

    def test_requires_login(self) -> None:
        response = self.client.get(reverse("medication_list"))
        self.assertEqual(response.status_code, 302)

    def test_renders_active_medications(self) -> None:
        self.client.force_login(self.patient)
        response = self.client.get(reverse("medication_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Aspirin")


class LogMedicationTakenViewTests(TestCase):
    """Tests for :func:`log_medication_taken_view`."""

    def setUp(self) -> None:
        self.client = Client()
        self.patient = User.objects.create(
            username="pat",
            pin="0000",
            role=User.Role.PATIENT,
        )
        self.med = Medication.objects.create(
            patient=self.patient,
            name="Aspirin",
        )
        self.client.force_login(self.patient)

    def test_get_redirects_to_medication_list(self) -> None:
        response = self.client.get(reverse("log_medication_taken"))
        self.assertRedirects(
            response,
            reverse("medication_list"),
            fetch_redirect_response=False,
        )

    def test_post_creates_log(self) -> None:
        response = self.client.post(
            reverse("log_medication_taken"),
            data={"medication_id": self.med.pk},
        )
        self.assertRedirects(
            response,
            reverse("medication_list"),
            fetch_redirect_response=False,
        )
        self.assertTrue(MedicationLog.objects.filter(medication=self.med).exists())

    def test_post_for_other_patient_med_returns_404(self) -> None:
        other = User.objects.create(
            username="other",
            pin="0000",
            role=User.Role.PATIENT,
        )
        other_med = Medication.objects.create(patient=other, name="Not mine")
        response = self.client.post(
            reverse("log_medication_taken"),
            data={"medication_id": other_med.pk},
        )
        self.assertEqual(response.status_code, 404)
        self.assertFalse(MedicationLog.objects.exists())

    def test_post_for_inactive_med_returns_404(self) -> None:
        self.med.is_active = False
        self.med.save()
        response = self.client.post(
            reverse("log_medication_taken"),
            data={"medication_id": self.med.pk},
        )
        self.assertEqual(response.status_code, 404)


class MedicationLogDetailEditDeleteTests(TestCase):
    """Tests for medication-log detail, edit, and delete pages."""

    def setUp(self) -> None:
        self.client = Client()
        self.patient = User.objects.create(
            username="pat",
            pin="0000",
            role=User.Role.PATIENT,
        )
        self.other = User.objects.create(
            username="other",
            pin="0000",
            role=User.Role.PATIENT,
        )
        self.med = Medication.objects.create(patient=self.patient, name="Aspirin", dosage="10mg")
        self.log = MedicationLog.objects.create(medication=self.med)
        self.client.force_login(self.patient)

    def test_detail_renders_medication(self) -> None:
        response = self.client.get(reverse("medication_log_detail", kwargs={"pk": self.log.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Aspirin")
        self.assertContains(response, "10mg")

    def test_detail_404_for_other_patient(self) -> None:
        other_med = Medication.objects.create(patient=self.other, name="Other med")
        other_log = MedicationLog.objects.create(medication=other_med)
        response = self.client.get(reverse("medication_log_detail", kwargs={"pk": other_log.pk}))
        self.assertEqual(response.status_code, 404)

    def test_edit_updates_timestamp(self) -> None:
        new_time = timezone.localtime(self.log.taken_at) - timedelta(hours=2)
        response = self.client.post(
            reverse("medication_log_edit", kwargs={"pk": self.log.pk}),
            data={"timestamp": new_time.strftime("%Y-%m-%dT%H:%M")},
        )
        self.assertRedirects(
            response,
            reverse("medication_log_detail", kwargs={"pk": self.log.pk}),
            fetch_redirect_response=False,
        )
        self.log.refresh_from_db()
        self.assertEqual(
            timezone.localtime(self.log.taken_at).strftime("%Y-%m-%dT%H:%M"),
            new_time.strftime("%Y-%m-%dT%H:%M"),
        )

    def test_delete_post_removes_record(self) -> None:
        response = self.client.post(reverse("medication_log_delete", kwargs={"pk": self.log.pk}))
        self.assertRedirects(response, reverse("activity_list"), fetch_redirect_response=False)
        self.assertFalse(MedicationLog.objects.filter(pk=self.log.pk).exists())


class MedicationStopRestartViewTests(TestCase):
    """Tests for :func:`medication_stop_view` and :func:`medication_restart_view`."""

    def setUp(self) -> None:
        self.client = Client()
        self.patient = User.objects.create(
            username="pat",
            pin="0000",
            role=User.Role.PATIENT,
        )
        self.other = User.objects.create(
            username="other",
            pin="0000",
            role=User.Role.PATIENT,
        )
        self.med = Medication.objects.create(patient=self.patient, name="Aspirin")
        self.client.force_login(self.patient)

    def test_stop_get_renders_form(self) -> None:
        response = self.client.get(reverse("medication_stop", kwargs={"pk": self.med.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Aspirin")

    def test_stop_post_marks_inactive(self) -> None:
        response = self.client.post(
            reverse("medication_stop", kwargs={"pk": self.med.pk}),
            data={"stop_reason": Medication.StopReason.SYMPTOMS, "stopped_at": "2026-05-16"},
        )
        self.assertRedirects(response, reverse("medication_list"), fetch_redirect_response=False)
        self.med.refresh_from_db()
        self.assertFalse(self.med.is_active)
        self.assertEqual(self.med.stop_reason, Medication.StopReason.SYMPTOMS)
        self.assertEqual(self.med.stopped_at.isoformat(), "2026-05-16")

    def test_stop_other_patient_returns_404(self) -> None:
        other_med = Medication.objects.create(patient=self.other, name="Theirs")
        response = self.client.post(
            reverse("medication_stop", kwargs={"pk": other_med.pk}),
            data={"stop_reason": Medication.StopReason.OUT, "stopped_at": "2026-05-16"},
        )
        self.assertEqual(response.status_code, 404)

    def test_stopped_medication_hidden_from_list(self) -> None:
        self.client.post(
            reverse("medication_stop", kwargs={"pk": self.med.pk}),
            data={"stop_reason": Medication.StopReason.OUT, "stopped_at": "2026-05-16"},
        )
        response = self.client.get(reverse("medication_list"))
        self.assertNotContains(response, "Catat Sudah Diminum")
        self.assertContains(response, "Aktifkan kembali")

    def test_log_taken_404_after_stop(self) -> None:
        self.client.post(
            reverse("medication_stop", kwargs={"pk": self.med.pk}),
            data={"stop_reason": Medication.StopReason.OUT, "stopped_at": "2026-05-16"},
        )
        response = self.client.post(
            reverse("log_medication_taken"),
            data={"medication_id": self.med.pk},
        )
        self.assertEqual(response.status_code, 404)

    def test_restart_post_clears_stop_fields(self) -> None:
        self.med.is_active = False
        self.med.stop_reason = Medication.StopReason.OUT
        self.med.stopped_at = timezone.localdate()
        self.med.save()
        response = self.client.post(reverse("medication_restart", kwargs={"pk": self.med.pk}))
        self.assertRedirects(response, reverse("medication_list"), fetch_redirect_response=False)
        self.med.refresh_from_db()
        self.assertTrue(self.med.is_active)
        self.assertEqual(self.med.stop_reason, "")
        self.assertIsNone(self.med.stopped_at)

    def test_restart_get_redirects(self) -> None:
        response = self.client.get(reverse("medication_restart", kwargs={"pk": self.med.pk}))
        self.assertRedirects(response, reverse("medication_list"), fetch_redirect_response=False)

    def test_restart_other_patient_returns_404(self) -> None:
        other_med = Medication.objects.create(
            patient=self.other,
            name="Theirs",
            is_active=False,
        )
        response = self.client.post(reverse("medication_restart", kwargs={"pk": other_med.pk}))
        self.assertEqual(response.status_code, 404)
