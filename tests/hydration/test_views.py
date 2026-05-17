"""Tests for the hydration views."""

from __future__ import annotations

from datetime import timedelta

from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from health_tracker.apps.hydration.models import WaterIntakeLog
from health_tracker.apps.users.models import User


class LogWaterViewTests(TestCase):
    """Tests for :func:`log_water_view`."""

    def setUp(self) -> None:
        self.client = Client()
        self.patient = User.objects.create(
            username="pat",
            pin="0000",
            role=User.Role.PATIENT,
        )
        self.client.force_login(self.patient)

    def test_get_renders_form(self) -> None:
        response = self.client.get(reverse("log_water"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "hydration/log_water_form.html")
        self.assertFalse(WaterIntakeLog.objects.exists())

    def test_post_with_custom_volume_creates_log(self) -> None:
        response = self.client.post(
            reverse("log_water"),
            data={"volume_ml": 320},
        )
        self.assertRedirects(response, reverse("water"), fetch_redirect_response=False)
        log = WaterIntakeLog.objects.get()
        self.assertEqual(log.volume_ml, 320)

    def test_post_with_notes_persists_notes(self) -> None:
        self.client.post(
            reverse("log_water"),
            data={"volume_ml": 250, "notes": "  setelah olahraga  "},
        )
        log = WaterIntakeLog.objects.get()
        self.assertEqual(log.notes, "setelah olahraga")

    def test_post_with_next_param_redirects_there(self) -> None:
        response = self.client.post(
            reverse("log_water"),
            data={"volume_ml": 500, "next": "/"},
        )
        self.assertRedirects(response, "/", fetch_redirect_response=False)

    def test_post_above_max_rerenders_form(self) -> None:
        response = self.client.post(
            reverse("log_water"),
            data={"volume_ml": 5000},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "hydration/log_water_form.html")
        self.assertFalse(WaterIntakeLog.objects.exists())

    def test_post_with_zero_is_rejected(self) -> None:
        self.client.post(
            reverse("log_water"),
            data={"volume_ml": 0},
        )
        self.assertFalse(WaterIntakeLog.objects.exists())

    def test_post_with_non_integer_rerenders_form(self) -> None:
        response = self.client.post(
            reverse("log_water"),
            data={"volume_ml": "abc"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "hydration/log_water_form.html")
        self.assertFalse(WaterIntakeLog.objects.exists())


class WaterViewTests(TestCase):
    """Tests for :func:`water_view`."""

    def setUp(self) -> None:
        self.client = Client()
        self.patient = User.objects.create(
            username="pat",
            pin="0000",
            role=User.Role.PATIENT,
        )

    def test_requires_login(self) -> None:
        response = self.client.get(reverse("water"))
        self.assertEqual(response.status_code, 302)

    def test_renders_total_and_drinks(self) -> None:
        self.patient.daily_water_target_ml = 1500
        self.patient.save(update_fields=["daily_water_target_ml"])
        WaterIntakeLog.objects.create(patient=self.patient, volume_ml=250)
        WaterIntakeLog.objects.create(patient=self.patient, volume_ml=500)
        self.client.force_login(self.patient)
        response = self.client.get(reverse("water"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "750")
        self.assertContains(response, "dari 1500 ml")

    def test_daily_target_defaults_to_750(self) -> None:
        self.client.force_login(self.patient)
        response = self.client.get(reverse("water"))
        self.assertContains(response, "dari 750 ml")


class DrinkDetailEditDeleteTests(TestCase):
    """Tests for drink detail, edit, and delete pages."""

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
        self.drink = WaterIntakeLog.objects.create(patient=self.patient, volume_ml=250)
        self.client.force_login(self.patient)

    def test_detail_renders_volume(self) -> None:
        response = self.client.get(reverse("drink_detail", kwargs={"pk": self.drink.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "250 ml")

    def test_detail_404_for_other_patient(self) -> None:
        other_drink = WaterIntakeLog.objects.create(patient=self.other, volume_ml=500)
        response = self.client.get(reverse("drink_detail", kwargs={"pk": other_drink.pk}))
        self.assertEqual(response.status_code, 404)

    def test_edit_updates_volume_and_timestamp(self) -> None:
        new_time = timezone.localtime(self.drink.created_at) - timedelta(hours=1)
        response = self.client.post(
            reverse("drink_edit", kwargs={"pk": self.drink.pk}),
            data={
                "timestamp": new_time.strftime("%Y-%m-%dT%H:%M"),
                "volume_ml": 400,
            },
        )
        self.assertRedirects(
            response,
            reverse("drink_detail", kwargs={"pk": self.drink.pk}),
            fetch_redirect_response=False,
        )
        self.drink.refresh_from_db()
        self.assertEqual(self.drink.volume_ml, 400)

    def test_edit_rejects_volume_above_max(self) -> None:
        response = self.client.post(
            reverse("drink_edit", kwargs={"pk": self.drink.pk}),
            data={
                "timestamp": timezone.localtime(self.drink.created_at).strftime("%Y-%m-%dT%H:%M"),
                "volume_ml": 5000,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.drink.refresh_from_db()
        self.assertEqual(self.drink.volume_ml, 250)

    def test_delete_post_removes_record(self) -> None:
        response = self.client.post(reverse("drink_delete", kwargs={"pk": self.drink.pk}))
        self.assertRedirects(response, reverse("activity_list"), fetch_redirect_response=False)
        self.assertFalse(WaterIntakeLog.objects.filter(pk=self.drink.pk).exists())
