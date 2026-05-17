"""Views for the hydration app."""

from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from health_tracker.apps.hydration.forms import WaterEntryEditForm, WaterEntryForm
from health_tracker.apps.hydration.models import WaterIntakeLog
from health_tracker.apps.hydration.utils import (
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
    daily_target_ml = patient.daily_water_target_ml
    progress_pct = min(int(round((total_ml / daily_target_ml) * 100)), 100) if daily_target_ml else 0
    context = {
        "total_ml": total_ml,
        "daily_target_ml": daily_target_ml,
        "progress_pct": progress_pct,
        "drinks": drinks,
    }
    return render(request, "hydration/water_intake.html", context)


@login_required
def log_water_view(request: HttpRequest) -> HttpResponse:
    """Render and process the form for logging a water-intake event.

    On GET, renders the form. On POST, saves the entry when valid and
    redirects to the water dashboard (or ``next``); on invalid POST,
    re-renders the form with errors.

    Args:
        request: The incoming HTTP request.

    Returns:
        The rendered form template or a redirect after a successful
        save.
    """
    patient = request.user.get_patient()

    if request.method == "POST":
        form = WaterEntryForm(request.POST)
        if form.is_valid():
            WaterIntakeLog.objects.create(
                patient=patient,
                volume_ml=form.cleaned_data["volume_ml"],
                notes=form.cleaned_data["notes"],
            )
            next_url = request.POST.get("next") or "water"
            return redirect(next_url)
    else:
        form = WaterEntryForm()

    context = {
        "form": form,
        "now": timezone.localtime(),
    }
    return render(request, "hydration/log_water_form.html", context)


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
