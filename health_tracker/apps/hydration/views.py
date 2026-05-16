"""Views for the hydration app."""

from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from health_tracker.apps.hydration.forms import WaterEntryEditForm, WaterEntryForm
from health_tracker.apps.hydration.models import WaterIntakeLog
from health_tracker.apps.hydration.utils import (
    DAILY_TARGET_ML,
    get_today_total_ml,
    get_today_water_logs,
)


@login_required
def water_view(request: HttpRequest) -> HttpResponse:
    """Render the water-intake page for the resolved patient.

    Args:
        request: The incoming HTTP request.

    Returns:
        The rendered water-intake template.
    """
    patient = request.user.get_patient()
    total_ml = get_today_total_ml(patient)
    drinks = list(get_today_water_logs(patient))
    progress_pct = min(int(round((total_ml / DAILY_TARGET_ML) * 100)), 100) if DAILY_TARGET_ML else 0
    context = {
        "form": WaterEntryForm(),
        "total_ml": total_ml,
        "daily_target_ml": DAILY_TARGET_ML,
        "progress_pct": progress_pct,
        "drinks": drinks,
    }
    return render(request, "hydration/water_intake.html", context)


@login_required
def log_water_view(request: HttpRequest) -> HttpResponse:
    """Record a water-intake event for the resolved patient.

    POST only. GET requests redirect silently to ``/``. The submitted
    volume must be a positive integer within
    ``[MIN_VOLUME_ML, MAX_VOLUME_ML]``; any other value is rejected
    silently.

    Args:
        request: The incoming HTTP request.

    Returns:
        A redirect to the water-intake page on success or rejection.
    """
    if request.method != "POST":
        return redirect("/")

    patient = request.user.get_patient()
    form = WaterEntryForm(request.POST)
    if not form.is_valid():
        return redirect("water")

    WaterIntakeLog.objects.create(
        patient=patient,
        volume_ml=form.cleaned_data["volume_ml"],
    )
    next_url = request.POST.get("next") or "water"
    return redirect(next_url)


def _get_owned_drink(request: HttpRequest, pk: int) -> WaterIntakeLog:
    """Return the drink ``pk`` if it belongs to the resolved patient."""
    patient = request.user.get_patient()
    return get_object_or_404(WaterIntakeLog, pk=pk, patient=patient)


@login_required
def drink_detail_view(request: HttpRequest, pk: int) -> HttpResponse:
    """Render the detail page for one ``WaterIntakeLog``."""
    drink = _get_owned_drink(request, pk)
    return render(request, "hydration/drink_detail.html", {"drink": drink})


@login_required
def drink_edit_view(request: HttpRequest, pk: int) -> HttpResponse:
    """Render and process the drink edit form."""
    drink = _get_owned_drink(request, pk)

    if request.method == "POST":
        form = WaterEntryEditForm(request.POST)
        if form.is_valid():
            form.apply(drink)
            return redirect("drink_detail", pk=drink.pk)
    else:
        form = WaterEntryEditForm(initial=WaterEntryEditForm.initial_for(drink))

    return render(request, "hydration/drink_edit.html", {"form": form, "drink": drink})


@login_required
def drink_delete_view(request: HttpRequest, pk: int) -> HttpResponse:
    """Render the delete-confirmation page and handle the deletion."""
    drink = _get_owned_drink(request, pk)
    if request.method == "POST":
        drink.delete()
        return redirect("activity_list")
    return render(request, "hydration/drink_delete.html", {"drink": drink})
