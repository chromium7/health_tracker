"""Tests for the unified activity list form, view, and metric CRUD pages."""

from __future__ import annotations

from datetime import timedelta

from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from health_tracker.apps.hydration.models import WaterIntakeLog
from health_tracker.apps.medications.models import Medication, MedicationLog
from health_tracker.apps.metrics.forms import ActivityHistoryForm
from health_tracker.apps.metrics.models import HealthMetric
from health_tracker.apps.users.models import User


class ActivityHistoryFormTests(TestCase):
    """Tests for :class:`ActivityHistoryForm`."""

    def setUp(self) -> None:
        self.patient = User.objects.create(
            username="pat",
            pin="0000",
            role=User.Role.PATIENT,
        )

    def test_unfiltered_returns_all_activity_kinds(self) -> None:
        HealthMetric.objects.create(
            patient=self.patient,
            metric_type=HealthMetric.MetricType.BLOOD_PRESSURE,
            value={"systolic": 120, "diastolic": 80},
        )
        WaterIntakeLog.objects.create(patient=self.patient, volume_ml=250)
        med = Medication.objects.create(patient=self.patient, name="Aspirin")
        MedicationLog.objects.create(medication=med)

        form = ActivityHistoryForm(patient=self.patient)
        activities = form.get_activities()
        kinds = {item.kind for item in activities}
        self.assertEqual(kinds, {"metric", "water", "medication"})

    def test_type_filter_narrows_to_metric(self) -> None:
        HealthMetric.objects.create(
            patient=self.patient,
            metric_type=HealthMetric.MetricType.BLOOD_PRESSURE,
            value={"systolic": 120, "diastolic": 80},
        )
        HealthMetric.objects.create(
            patient=self.patient,
            metric_type=HealthMetric.MetricType.HEART_RATE,
            value={"value": 75},
        )
        WaterIntakeLog.objects.create(patient=self.patient, volume_ml=250)

        form = ActivityHistoryForm({"activity_type": "metric:bp"}, patient=self.patient)
        self.assertTrue(form.is_valid())
        activities = form.get_activities()
        self.assertEqual(len(activities), 1)
        self.assertEqual(activities[0].kind, "metric")
        self.assertEqual(activities[0].metric_type, HealthMetric.MetricType.BLOOD_PRESSURE)

    def test_type_filter_narrows_to_water(self) -> None:
        HealthMetric.objects.create(
            patient=self.patient,
            metric_type=HealthMetric.MetricType.BLOOD_PRESSURE,
            value={"systolic": 120, "diastolic": 80},
        )
        WaterIntakeLog.objects.create(patient=self.patient, volume_ml=250)

        form = ActivityHistoryForm({"activity_type": "water"}, patient=self.patient)
        self.assertTrue(form.is_valid())
        activities = form.get_activities()
        self.assertEqual(len(activities), 1)
        self.assertEqual(activities[0].kind, "water")

    def test_date_range_narrows_results(self) -> None:
        recent = HealthMetric.objects.create(
            patient=self.patient,
            metric_type=HealthMetric.MetricType.BLOOD_PRESSURE,
            value={"systolic": 120, "diastolic": 80},
        )
        older = HealthMetric.objects.create(
            patient=self.patient,
            metric_type=HealthMetric.MetricType.BLOOD_PRESSURE,
            value={"systolic": 130, "diastolic": 85},
        )
        HealthMetric.objects.filter(pk=older.pk).update(created_at=timezone.now() - timedelta(days=10))
        today = timezone.localdate().isoformat()
        form = ActivityHistoryForm(
            {"start_date": today, "end_date": today, "activity_type": "metric:bp"},
            patient=self.patient,
        )
        self.assertTrue(form.is_valid(), form.errors)
        ids = [item.object_id for item in form.get_activities()]
        self.assertEqual(ids, [recent.pk])

    def test_inverted_range_is_invalid(self) -> None:
        form = ActivityHistoryForm(
            {"start_date": "2026-12-31", "end_date": "2026-01-01"},
            patient=self.patient,
        )
        self.assertFalse(form.is_valid())


class ActivityListViewTests(TestCase):
    """Tests for :func:`activity_list_view`."""

    def setUp(self) -> None:
        self.client = Client()
        self.patient = User.objects.create(
            username="pat",
            first_name="Adi",
            pin="0000",
            role=User.Role.PATIENT,
        )

    def test_requires_login(self) -> None:
        response = self.client.get(reverse("activity_list"))
        self.assertEqual(response.status_code, 302)

    def test_renders_patient_name_and_all_activities(self) -> None:
        HealthMetric.objects.create(
            patient=self.patient,
            metric_type=HealthMetric.MetricType.BLOOD_PRESSURE,
            value={"systolic": 128, "diastolic": 82},
        )
        WaterIntakeLog.objects.create(patient=self.patient, volume_ml=250)
        self.client.force_login(self.patient)
        response = self.client.get(reverse("activity_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Aktivitas Terbaru")
        self.assertContains(response, "Adi")
        self.assertContains(response, "128/82")
        self.assertContains(response, "250 ml")

    def test_filter_by_type(self) -> None:
        HealthMetric.objects.create(
            patient=self.patient,
            metric_type=HealthMetric.MetricType.BLOOD_PRESSURE,
            value={"systolic": 128, "diastolic": 82},
        )
        WaterIntakeLog.objects.create(patient=self.patient, volume_ml=250)
        self.client.force_login(self.patient)
        response = self.client.get(reverse("activity_list"), data={"activity_type": "water"})
        self.assertContains(response, "250 ml")
        self.assertNotContains(response, "128/82")

    def test_inverted_range_is_rejected(self) -> None:
        self.client.force_login(self.patient)
        response = self.client.get(
            reverse("activity_list"),
            data={"start_date": "2026-12-31", "end_date": "2026-01-01"},
        )
        self.assertContains(response, "Tanggal mulai harus sebelum atau sama dengan tanggal akhir.")


class MetricDetailEditDeleteTests(TestCase):
    """Tests for the metric detail, edit, and delete views."""

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
        self.metric = HealthMetric.objects.create(
            patient=self.patient,
            metric_type=HealthMetric.MetricType.BLOOD_PRESSURE,
            value={"systolic": 120, "diastolic": 80, "heart_rate": 72},
            notes="Resting",
        )
        self.client.force_login(self.patient)

    def test_detail_renders_value_and_notes(self) -> None:
        response = self.client.get(reverse("metric_detail", kwargs={"pk": self.metric.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "120/80")
        self.assertContains(response, "Resting")

    def test_detail_404_for_other_patient(self) -> None:
        other_metric = HealthMetric.objects.create(
            patient=self.other,
            metric_type=HealthMetric.MetricType.HEART_RATE,
            value={"value": 70},
        )
        response = self.client.get(reverse("metric_detail", kwargs={"pk": other_metric.pk}))
        self.assertEqual(response.status_code, 404)

    def test_edit_updates_value_and_timestamp(self) -> None:
        new_time = timezone.localtime(self.metric.created_at) - timedelta(hours=2)
        response = self.client.post(
            reverse("metric_edit", kwargs={"pk": self.metric.pk}),
            data={
                "timestamp": new_time.strftime("%Y-%m-%dT%H:%M"),
                "systolic": 130,
                "diastolic": 85,
                "heart_rate": 70,
                "notes": "Updated",
            },
        )
        self.assertRedirects(
            response,
            reverse("metric_detail", kwargs={"pk": self.metric.pk}),
            fetch_redirect_response=False,
        )
        self.metric.refresh_from_db()
        self.assertEqual(self.metric.value, {"systolic": 130, "diastolic": 85, "heart_rate": 70})
        self.assertEqual(self.metric.notes, "Updated")

    def test_edit_rejects_invalid_blood_pressure(self) -> None:
        response = self.client.post(
            reverse("metric_edit", kwargs={"pk": self.metric.pk}),
            data={
                "timestamp": timezone.localtime(self.metric.created_at).strftime("%Y-%m-%dT%H:%M"),
                "systolic": 80,
                "diastolic": 120,
                "heart_rate": 70,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.metric.refresh_from_db()
        self.assertEqual(self.metric.value["systolic"], 120)

    def test_delete_get_renders_confirmation(self) -> None:
        response = self.client.get(reverse("metric_delete", kwargs={"pk": self.metric.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Yakin ingin menghapus")

    def test_delete_post_removes_record(self) -> None:
        response = self.client.post(reverse("metric_delete", kwargs={"pk": self.metric.pk}))
        self.assertRedirects(response, reverse("activity_list"), fetch_redirect_response=False)
        self.assertFalse(HealthMetric.objects.filter(pk=self.metric.pk).exists())
