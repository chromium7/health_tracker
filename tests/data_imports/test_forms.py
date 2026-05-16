"""Tests for the CSV import form and parser."""

from __future__ import annotations

from datetime import datetime

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone

from health_tracker.apps.data_imports.forms import CSVImportForm
from health_tracker.apps.data_imports.utils import parse_csv, parse_datetime
from health_tracker.apps.hydration.models import WaterIntakeLog
from health_tracker.apps.medications.models import Medication, MedicationLog
from health_tracker.apps.metrics.models import HealthMetric
from health_tracker.apps.users.models import User


def _csv(rows: list[str]) -> SimpleUploadedFile:
    """Build an in-memory CSV upload from a list of pre-formatted lines."""
    content = "\n".join(rows).encode("utf-8")
    return SimpleUploadedFile("import.csv", content, content_type="text/csv")


class ParseDatetimeTests(TestCase):
    """Tests for :func:`parse_datetime`."""

    def test_accepts_full_iso_form(self) -> None:
        result = parse_datetime("2026-05-10T08:30:00")
        self.assertTrue(timezone.is_aware(result))
        self.assertEqual(timezone.localtime(result).year, 2026)
        self.assertEqual(timezone.localtime(result).hour, 8)

    def test_accepts_space_separator(self) -> None:
        result = parse_datetime("2026-05-10 08:30")
        self.assertEqual(timezone.localtime(result).minute, 30)

    def test_accepts_date_only(self) -> None:
        result = parse_datetime("2026-05-10")
        local = timezone.localtime(result)
        self.assertEqual(local.hour, 0)
        self.assertEqual(local.minute, 0)

    def test_rejects_garbage(self) -> None:
        with self.assertRaises(ValueError):
            parse_datetime("not-a-date")

    def test_rejects_blank(self) -> None:
        with self.assertRaises(ValueError):
            parse_datetime("")


class ParseCSVTests(TestCase):
    """Tests for :func:`parse_csv` row-level validation."""

    def setUp(self) -> None:
        self.patient = User.objects.create(
            username="pat",
            pin="0000",
            role=User.Role.PATIENT,
        )
        self.medication = Medication.objects.create(patient=self.patient, name="Aspirin")

    def test_missing_required_header_aborts(self) -> None:
        upload = _csv(["activity_type,notes", "bp,no created_at column"])
        parsed, errors = parse_csv(upload.read(), self.patient)
        self.assertEqual(parsed.total, 0)
        self.assertEqual(len(errors), 1)
        self.assertIn("Missing required column", errors[0].message)

    def test_empty_csv_aborts(self) -> None:
        upload = _csv([""])
        parsed, errors = parse_csv(upload.read(), self.patient)
        self.assertEqual(parsed.total, 0)
        self.assertEqual(len(errors), 1)

    def test_unknown_activity_type_is_per_row_error(self) -> None:
        upload = _csv(
            [
                "activity_type,created_at",
                "rocket,2026-05-10 08:00",
            ]
        )
        _, errors = parse_csv(upload.read(), self.patient)
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].line, 2)
        self.assertIn("unknown activity_type", errors[0].message)

    def test_bp_requires_systolic_and_diastolic(self) -> None:
        upload = _csv(
            [
                "activity_type,created_at,systolic,diastolic",
                "bp,2026-05-10 08:00,,80",
            ]
        )
        _, errors = parse_csv(upload.read(), self.patient)
        self.assertEqual(len(errors), 1)
        self.assertIn("systolic", errors[0].message)

    def test_bp_rejects_systolic_not_greater_than_diastolic(self) -> None:
        upload = _csv(
            [
                "activity_type,created_at,systolic,diastolic",
                "bp,2026-05-10 08:00,80,80",
            ]
        )
        _, errors = parse_csv(upload.read(), self.patient)
        self.assertEqual(len(errors), 1)
        self.assertIn("greater than diastolic", errors[0].message)

    def test_bp_row_optional_heart_rate(self) -> None:
        upload = _csv(
            [
                "activity_type,created_at,systolic,diastolic,heart_rate,notes",
                "bp,2026-05-10 08:00,120,80,72,morning",
                "bp,2026-05-10 18:00,118,79,,evening",
            ]
        )
        parsed, errors = parse_csv(upload.read(), self.patient)
        self.assertEqual(errors, [])
        self.assertEqual(len(parsed.metrics), 2)
        self.assertEqual(parsed.metrics[0].value, {"systolic": 120, "diastolic": 80, "heart_rate": 72})
        self.assertEqual(parsed.metrics[1].value, {"systolic": 118, "diastolic": 79})

    def test_weight_uses_float_value(self) -> None:
        upload = _csv(
            [
                "activity_type,created_at,weight_kg",
                "wt,2026-05-10 08:00,72.4",
            ]
        )
        parsed, errors = parse_csv(upload.read(), self.patient)
        self.assertEqual(errors, [])
        self.assertEqual(parsed.metrics[0].value, {"value": 72.4})

    def test_medication_id_must_belong_to_patient(self) -> None:
        other = User.objects.create(username="other", pin="1111", role=User.Role.PATIENT)
        foreign = Medication.objects.create(patient=other, name="Foreign")
        upload = _csv(
            [
                "activity_type,created_at,medication_id",
                f"medication,2026-05-10 08:00,{foreign.pk}",
            ]
        )
        _, errors = parse_csv(upload.read(), self.patient)
        self.assertEqual(len(errors), 1)
        self.assertIn("does not exist", errors[0].message)

    def test_medication_id_for_own_medication_is_valid(self) -> None:
        upload = _csv(
            [
                "activity_type,created_at,medication_id",
                f"medication,2026-05-10 08:00,{self.medication.pk}",
            ]
        )
        parsed, errors = parse_csv(upload.read(), self.patient)
        self.assertEqual(errors, [])
        self.assertEqual(len(parsed.medication_logs), 1)
        self.assertEqual(parsed.medication_logs[0].medication_id, self.medication.pk)

    def test_water_volume_must_be_positive(self) -> None:
        upload = _csv(
            [
                "activity_type,created_at,volume_ml",
                "water,2026-05-10 08:00,0",
            ]
        )
        _, errors = parse_csv(upload.read(), self.patient)
        self.assertEqual(len(errors), 1)
        self.assertIn("positive", errors[0].message)

    def test_mixed_activity_types_in_one_csv(self) -> None:
        upload = _csv(
            [
                "activity_type,created_at,systolic,diastolic,heart_rate,weight_kg,spo2,volume_ml,medication_id,notes",
                "bp,2026-05-10 08:00,120,80,72,,,,,",
                "water,2026-05-10 09:00,,,,,,250,,",
                "wt,2026-05-10 10:00,,,,71.2,,,,",
                f"medication,2026-05-10 11:00,,,,,,,{self.medication.pk},",
                "os,2026-05-10 12:00,,,,,98,,,",
                "hr,2026-05-10 13:00,,,80,,,,,",
            ]
        )
        parsed, errors = parse_csv(upload.read(), self.patient)
        self.assertEqual(errors, [])
        self.assertEqual(len(parsed.metrics), 4)
        self.assertEqual(len(parsed.waters), 1)
        self.assertEqual(len(parsed.medication_logs), 1)


class ImportDataTests(TestCase):
    """End-to-end tests for :meth:`CSVImportForm.import_data`."""

    def setUp(self) -> None:
        self.patient = User.objects.create(
            username="pat",
            pin="0000",
            role=User.Role.PATIENT,
        )
        self.medication = Medication.objects.create(patient=self.patient, name="Aspirin")

    def _build_form(self, lines: list[str]) -> CSVImportForm:
        upload = _csv(lines)
        return CSVImportForm(
            data={"patient": self.patient.pk},
            files={"csv_file": upload},
        )

    def test_successful_import_persists_records_with_imported_timestamps(self) -> None:
        form = self._build_form(
            [
                "activity_type,created_at,systolic,diastolic,heart_rate,weight_kg,spo2,volume_ml,medication_id,notes",
                "bp,2026-05-10 08:00,120,80,72,,,,,morning reading",
                "water,2026-05-10 09:00,,,,,,250,,",
                f"medication,2026-05-10 11:00,,,,,,,{self.medication.pk},",
            ]
        )
        self.assertTrue(form.is_valid(), form.errors)
        result = form.import_data()
        self.assertTrue(result.success)
        self.assertEqual(result.metric_count, 1)
        self.assertEqual(result.water_count, 1)
        self.assertEqual(result.medication_log_count, 1)

        metric = HealthMetric.objects.get()
        self.assertEqual(metric.patient, self.patient)
        self.assertEqual(metric.notes, "morning reading")
        self.assertEqual(
            timezone.localtime(metric.created_at).replace(microsecond=0),
            timezone.make_aware(datetime(2026, 5, 10, 8, 0, 0)),
        )

        water = WaterIntakeLog.objects.get()
        self.assertEqual(water.volume_ml, 250)
        self.assertEqual(
            timezone.localtime(water.created_at).replace(microsecond=0),
            timezone.make_aware(datetime(2026, 5, 10, 9, 0, 0)),
        )

        log = MedicationLog.objects.get()
        self.assertEqual(log.medication, self.medication)
        self.assertEqual(
            timezone.localtime(log.taken_at).replace(microsecond=0),
            timezone.make_aware(datetime(2026, 5, 10, 11, 0, 0)),
        )

    def test_row_errors_abort_entire_import(self) -> None:
        form = self._build_form(
            [
                "activity_type,created_at,systolic,diastolic,volume_ml",
                "bp,2026-05-10 08:00,120,80,",
                "water,not-a-date,,,250",
            ]
        )
        self.assertTrue(form.is_valid())
        result = form.import_data()
        self.assertFalse(result.success)
        self.assertEqual(len(result.errors), 1)
        self.assertEqual(result.errors[0].line, 3)
        self.assertFalse(HealthMetric.objects.exists())
        self.assertFalse(WaterIntakeLog.objects.exists())

    def test_non_csv_extension_rejected_at_form_layer(self) -> None:
        upload = SimpleUploadedFile("import.txt", b"activity_type,created_at\n", content_type="text/plain")
        form = CSVImportForm(
            data={"patient": self.patient.pk},
            files={"csv_file": upload},
        )
        self.assertFalse(form.is_valid())
        self.assertIn("csv_file", form.errors)


class CSVImportViewTests(TestCase):
    """Tests for the admin CSV import view."""

    def setUp(self) -> None:
        self.patient = User.objects.create(
            username="pat",
            pin="0000",
            role=User.Role.PATIENT,
        )
        self.staff = User.objects.create(
            username="admin",
            pin="9999",
            role=User.Role.PATIENT,
            is_staff=True,
        )

    def test_requires_staff(self) -> None:
        response = self.client.get("/admin/import/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response["Location"])

    def test_get_renders_form(self) -> None:
        self.client.force_login(self.staff)
        response = self.client.get("/admin/import/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "activity_type")
        self.assertContains(response, "Import")

    def test_post_imports_records(self) -> None:
        self.client.force_login(self.staff)
        upload = _csv(
            [
                "activity_type,created_at,volume_ml",
                "water,2026-05-10 09:00,250",
            ]
        )
        response = self.client.post(
            "/admin/import/",
            data={"patient": self.patient.pk, "csv_file": upload},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(WaterIntakeLog.objects.count(), 1)
