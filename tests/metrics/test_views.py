"""Tests for the metrics views."""

from __future__ import annotations

from django.test import Client, TestCase
from django.urls import reverse

from health_tracker.apps.hydration.models import WaterIntakeLog
from health_tracker.apps.medications.models import Medication, MedicationLog
from health_tracker.apps.metrics.models import HealthMetric
from health_tracker.apps.users.models import User


class DashboardViewTests(TestCase):
    """Tests for :func:`dashboard_view`."""

    def setUp(self) -> None:
        self.client = Client()
        self.patient = User.objects.create(
            username="pat",
            pin="0000",
            role=User.Role.PATIENT,
        )

    def test_requires_login(self) -> None:
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response["Location"])

    def test_renders_for_patient(self) -> None:
        self.client.force_login(self.patient)
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Catatan Hari Ini")
        self.assertContains(response, "Catat Pengukuran")
        self.assertContains(response, "Aktivitas Terbaru")

    def test_does_not_show_feelings_prompt(self) -> None:
        self.client.force_login(self.patient)
        response = self.client.get(reverse("dashboard"))
        self.assertNotContains(response, "How are you feeling")
        self.assertNotContains(response, "Apa kabar")

    def test_recent_activities_include_water_and_medication(self) -> None:
        medication = Medication.objects.create(patient=self.patient, name="Aspirin")
        MedicationLog.objects.create(medication=medication)
        WaterIntakeLog.objects.create(patient=self.patient, volume_ml=250)
        HealthMetric.objects.create(
            patient=self.patient,
            metric_type=HealthMetric.MetricType.BLOOD_PRESSURE,
            value={"systolic": 120, "diastolic": 80},
        )
        self.client.force_login(self.patient)
        response = self.client.get(reverse("dashboard"))
        self.assertContains(response, "120/80")
        self.assertContains(response, "250 ml")
        self.assertContains(response, "Aspirin")

    def test_caregiver_sees_assigned_patient_data(self) -> None:
        caregiver = User.objects.create(
            username="care",
            pin="1111",
            role=User.Role.CAREGIVER,
            patient_profile=self.patient,
        )
        HealthMetric.objects.create(
            patient=self.patient,
            metric_type=HealthMetric.MetricType.BLOOD_PRESSURE,
            value={"systolic": 128, "diastolic": 82},
        )
        self.client.force_login(caregiver)
        response = self.client.get(reverse("dashboard"))
        self.assertContains(response, "128")
        self.assertContains(response, "82")


class LogMetricViewTests(TestCase):
    """Tests for :func:`log_metric_view`."""

    def setUp(self) -> None:
        self.client = Client()
        self.patient = User.objects.create(
            username="pat",
            pin="0000",
            role=User.Role.PATIENT,
        )
        self.client.force_login(self.patient)

    def test_unknown_metric_type_returns_404(self) -> None:
        response = self.client.get(reverse("log_metric", kwargs={"metric_type": "xx"}))
        self.assertEqual(response.status_code, 404)

    def test_get_renders_form(self) -> None:
        response = self.client.get(
            reverse("log_metric", kwargs={"metric_type": HealthMetric.MetricType.BLOOD_PRESSURE})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "systolic")
        self.assertContains(response, "diastolic")

    def test_post_creates_metric_and_redirects(self) -> None:
        response = self.client.post(
            reverse("log_metric", kwargs={"metric_type": HealthMetric.MetricType.BLOOD_PRESSURE}),
            data={
                "systolic": 120,
                "diastolic": 80,
                "heart_rate": 72,
                "notes": "Resting",
            },
        )
        self.assertRedirects(response, "/", fetch_redirect_response=False)
        metric = HealthMetric.objects.get(patient=self.patient)
        self.assertEqual(metric.metric_type, HealthMetric.MetricType.BLOOD_PRESSURE)
        self.assertEqual(metric.value, {"systolic": 120, "diastolic": 80, "heart_rate": 72})
        self.assertEqual(metric.notes, "Resting")

    def test_post_with_invalid_data_re_renders_form(self) -> None:
        response = self.client.post(
            reverse("log_metric", kwargs={"metric_type": HealthMetric.MetricType.BLOOD_PRESSURE}),
            data={"systolic": 80, "diastolic": 120},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(HealthMetric.objects.exists())
