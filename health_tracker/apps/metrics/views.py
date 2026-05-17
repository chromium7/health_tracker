"""Views for the metrics app: dashboard, activity log, and metric CRUD."""

from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from health_tracker.apps.hydration.utils import get_today_total_ml
from health_tracker.apps.medications.utils import get_medication_progress
from health_tracker.apps.metrics.forms import ActivityHistoryForm, MetricEditForm
from health_tracker.apps.metrics.models import HealthMetric
from health_tracker.apps.metrics.utils import (
    ACTIVITY_TYPE_CHOICES,
    METRIC_FORM_MAP,
    METRIC_LABELS_ID,
    METRIC_PAGE_TITLES,
    build_metric_value,
    get_latest_metrics,
    get_recent_activities,
)


@login_required
def dashboard_view(request: HttpRequest) -> HttpResponse:
    """Render the patient dashboard.

    Resolves the patient via ``get_patient()`` and assembles context
    from the metrics, medications, and hydration utilities.

    Args:
        request: The incoming HTTP request.

    Returns:
        The rendered dashboard template.
    """
    user = request.user
    patient = user.get_patient()
    latest = get_latest_metrics(patient)
    progress = get_medication_progress(patient)
    total_ml = get_today_total_ml(patient)

    context = {
        "today": timezone.localdate(),
        "user_first_name": user.first_name or user.username,
        "patient_full_name": patient.get_full_name().strip() or patient.username,
        "is_caregiver": user.is_caregiver,
        "latest_bp": latest[HealthMetric.MetricType.BLOOD_PRESSURE],
        "latest_weight": latest[HealthMetric.MetricType.WEIGHT],
        "medication_progress": progress,
        "total_ml": total_ml,
        "daily_target_ml": patient.daily_water_target_ml,
        "recent_activities": get_recent_activities(patient, limit=5),
    }
    return render(request, "dashboard.html", context)


@login_required
def log_metric_view(request: HttpRequest, metric_type: str) -> HttpResponse:
    """Render and process the form for logging a new metric reading.

    Args:
        request: The incoming HTTP request.
        metric_type: One of the ``HealthMetric.METRIC_*`` keys.

    Returns:
        The rendered form on GET / invalid POST, or a redirect to ``/``
        after a successful save.

    Raises:
        Http404: When ``metric_type`` is not a known metric type.
    """
    if metric_type not in METRIC_FORM_MAP:
        raise Http404("Unknown metric type.")

    patient = request.user.get_patient()
    form_class = METRIC_FORM_MAP[metric_type]

    if request.method == "POST":
        form = form_class(request.POST)
        if form.is_valid():
            HealthMetric.objects.create(
                patient=patient,
                metric_type=metric_type,
                value=build_metric_value(metric_type, form.cleaned_data),
                notes=form.cleaned_data.get("notes") or "",
            )
            return redirect("/")
    else:
        form = form_class()

    context = {
        "form": form,
        "metric_type": metric_type,
        "page_title": METRIC_PAGE_TITLES[metric_type],
        "metric_label": METRIC_LABELS_ID[metric_type],
        "now": timezone.localtime(),
    }
    return render(request, "metrics/log_metric_form.html", context)


@login_required
def activity_list_view(request: HttpRequest) -> HttpResponse:
    """Render the unified, filterable activity history page.

    The page lists metrics, drinks, and medication-taken events for
    the resolved patient. Supports filtering by activity type and
    date range.

    Args:
        request: The incoming HTTP request.

    Returns:
        The rendered activity list template.
    """
    patient = request.user.get_patient()
    form = ActivityHistoryForm(request.GET or None, patient=patient)
    page = form.get_page(request.GET.get("page"))
    context = {
        "form": form,
        "page": page,
        "patient_name": patient.get_full_name().strip() or patient.username,
        "filter_summary": form.applied_filter_summary,
        "type_choices": ACTIVITY_TYPE_CHOICES,
    }
    return render(request, "metrics/activity_list.html", context)


def _get_owned_metric(request: HttpRequest, pk: int) -> HealthMetric:
    """Return the ``HealthMetric`` ``pk`` if it belongs to the resolved patient."""
    patient = request.user.get_patient()
    return get_object_or_404(HealthMetric, pk=pk, patient=patient)


@login_required
def metric_detail_view(request: HttpRequest, pk: int) -> HttpResponse:
    """Render the detail page for one ``HealthMetric``.

    Args:
        request: The incoming HTTP request.
        pk: Primary key of the metric to display.

    Returns:
        The rendered detail template.
    """
    metric = _get_owned_metric(request, pk)
    context = {
        "metric": metric,
        "metric_label": METRIC_LABELS_ID[metric.metric_type],
    }
    return render(request, "metrics/metric_detail.html", context)


@login_required
def metric_edit_view(request: HttpRequest, pk: int) -> HttpResponse:
    """Render and process the metric edit form.

    Args:
        request: The incoming HTTP request.
        pk: Primary key of the metric to edit.

    Returns:
        The rendered form on GET / invalid POST, or a redirect to the
        detail page after a successful save.
    """
    metric = _get_owned_metric(request, pk)

    if request.method == "POST":
        form = MetricEditForm(request.POST, metric_type=metric.metric_type)
        if form.is_valid():
            form.apply(metric)
            return redirect("metric_detail", pk=metric.pk)
    else:
        form = MetricEditForm(
            initial=MetricEditForm.initial_for(metric),
            metric_type=metric.metric_type,
        )

    context = {
        "form": form,
        "metric": metric,
        "metric_label": METRIC_LABELS_ID[metric.metric_type],
    }
    return render(request, "metrics/metric_edit.html", context)


@login_required
def metric_delete_view(request: HttpRequest, pk: int) -> HttpResponse:
    """Render the delete-confirmation page and handle the deletion.

    GET renders a confirmation page. POST deletes the metric and
    redirects to the unified activity list.

    Args:
        request: The incoming HTTP request.
        pk: Primary key of the metric to delete.

    Returns:
        The rendered confirmation template, or a redirect on POST.
    """
    metric = _get_owned_metric(request, pk)
    if request.method == "POST":
        metric.delete()
        return redirect("activity_list")
    context = {
        "metric": metric,
        "metric_label": METRIC_LABELS_ID[metric.metric_type],
    }
    return render(request, "metrics/metric_delete.html", context)
