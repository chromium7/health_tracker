"""Tests for the metrics utility helpers."""

from __future__ import annotations

from decimal import Decimal

from django.test import TestCase

from health_tracker.apps.metrics.models import HealthMetric
from health_tracker.apps.metrics.utils import (
    METRIC_FORM_MAP,
    build_metric_value,
    get_latest_metrics,
)
from health_tracker.apps.users.models import User


class BuildMetricValueTests(TestCase):
    """Tests for :func:`build_metric_value`."""

    def test_blood_pressure(self) -> None:
        result = build_metric_value(
            HealthMetric.MetricType.BLOOD_PRESSURE,
            {"systolic": 120, "diastolic": 80, "heart_rate": 72},
        )
        self.assertEqual(result, {"systolic": 120, "diastolic": 80, "heart_rate": 72})

    def test_heart_rate(self) -> None:
        result = build_metric_value(
            HealthMetric.MetricType.HEART_RATE,
            {"value": Decimal("72")},
        )
        self.assertEqual(result, {"value": 72})

    def test_weight(self) -> None:
        result = build_metric_value(
            HealthMetric.MetricType.WEIGHT,
            {"value": Decimal("70.5")},
        )
        self.assertEqual(result, {"value": 70.5})

    def test_oxygen_saturation(self) -> None:
        result = build_metric_value(
            HealthMetric.MetricType.OXYGEN_SATURATION,
            {"value": Decimal("98")},
        )
        self.assertEqual(result, {"value": 98})

    def test_unknown_metric_type_raises(self) -> None:
        with self.assertRaises(ValueError):
            build_metric_value("xx", {"value": Decimal("1")})


class FormMapTests(TestCase):
    """Sanity checks for the metric -> form mapping."""

    def test_every_metric_has_a_form(self) -> None:
        for key, _ in HealthMetric.MetricType.choices:
            self.assertIn(key, METRIC_FORM_MAP)


class GetLatestMetricsTests(TestCase):
    """Tests for :func:`get_latest_metrics`."""

    def setUp(self) -> None:
        self.patient = User.objects.create(
            username="pat",
            pin="0000",
            role=User.Role.PATIENT,
        )

    def test_empty_when_no_readings(self) -> None:
        result = get_latest_metrics(self.patient)
        for key, _ in HealthMetric.MetricType.choices:
            self.assertIsNone(result[key])

    def test_returns_most_recent_per_type(self) -> None:
        older = HealthMetric.objects.create(
            patient=self.patient,
            metric_type=HealthMetric.MetricType.HEART_RATE,
            value={"value": 60},
        )
        newer = HealthMetric.objects.create(
            patient=self.patient,
            metric_type=HealthMetric.MetricType.HEART_RATE,
            value={"value": 70},
        )
        result = get_latest_metrics(self.patient)
        self.assertEqual(result[HealthMetric.MetricType.HEART_RATE], newer)
        self.assertNotEqual(result[HealthMetric.MetricType.HEART_RATE], older)

    def test_only_returns_metrics_for_given_patient(self) -> None:
        other = User.objects.create(
            username="other",
            pin="0000",
            role=User.Role.PATIENT,
        )
        HealthMetric.objects.create(
            patient=other,
            metric_type=HealthMetric.MetricType.HEART_RATE,
            value={"value": 60},
        )
        result = get_latest_metrics(self.patient)
        self.assertIsNone(result[HealthMetric.MetricType.HEART_RATE])
