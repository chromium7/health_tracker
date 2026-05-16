"""Views for the medications app."""

from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from health_tracker.apps.medications.forms import (
    MedicationLogEditForm,
    MedicationStopForm,
)
from health_tracker.apps.medications.models import Medication, MedicationLog
from health_tracker.apps.medications.utils import (
    get_medication_cards,
    get_medication_progress,
    get_stopped_medications,
)


@login_required
def medication_list_view(request: HttpRequest) -> HttpResponse:
    """Render the patient's medication list with 'taken today' status.

    Args:
        request: The incoming HTTP request.

    Returns:
        The rendered medication-list template.
    """
    patient = request.user.get_patient()
    context = {
        "cards": get_medication_cards(patient),
        "progress": get_medication_progress(patient),
        "stopped_medications": get_stopped_medications(patient),
    }
    return render(request, "medications/log_medication.html", context)


def _get_owned_medication(request: HttpRequest, pk: int) -> Medication:
    """Return the ``Medication`` ``pk`` if it belongs to the resolved patient."""
    patient = request.user.get_patient()
    return get_object_or_404(Medication, pk=pk, patient=patient)


@login_required
def medication_stop_view(request: HttpRequest, pk: int) -> HttpResponse:
    """Render and process the 'stop medication' form.

    Marks the medication inactive and records the reason and date.
    """
    medication = _get_owned_medication(request, pk)

    if request.method == "POST":
        form = MedicationStopForm(request.POST)
        if form.is_valid():
            form.apply(medication)
            return redirect("medication_list")
    else:
        form = MedicationStopForm(initial=MedicationStopForm.initial_data())

    return render(
        request,
        "medications/medication_stop.html",
        {"form": form, "medication": medication},
    )


@login_required
def medication_restart_view(request: HttpRequest, pk: int) -> HttpResponse:
    """Re-activate a previously stopped medication.

    POST only. Clears ``stop_reason`` and ``stopped_at`` and flips
    ``is_active`` back to ``True``.
    """
    if request.method != "POST":
        return redirect("medication_list")

    medication = _get_owned_medication(request, pk)
    medication.is_active = True
    medication.stop_reason = ""
    medication.stopped_at = None
    medication.save(update_fields=["is_active", "stop_reason", "stopped_at"])
    return redirect("medication_list")


@login_required
def log_medication_taken_view(request: HttpRequest) -> HttpResponse:
    """Create a ``MedicationLog`` for the posted medication.

    POST only. GET requests are redirected to the medication list.
    Ownership is verified before logging.

    Args:
        request: The incoming HTTP request.

    Returns:
        A redirect to the medication list.
    """
    if request.method != "POST":
        return redirect("medication_list")

    patient = request.user.get_patient()
    medication_id = request.POST.get("medication_id")
    medication = get_object_or_404(
        Medication,
        pk=medication_id,
        patient=patient,
        is_active=True,
    )
    MedicationLog.objects.create(medication=medication)
    return redirect("medication_list")


def _get_owned_log(request: HttpRequest, pk: int) -> MedicationLog:
    """Return the ``MedicationLog`` ``pk`` if owned by the resolved patient."""
    patient = request.user.get_patient()
    return get_object_or_404(
        MedicationLog.objects.select_related("medication__patient"),
        pk=pk,
        medication__patient=patient,
    )


@login_required
def medication_log_detail_view(request: HttpRequest, pk: int) -> HttpResponse:
    """Render the detail page for one ``MedicationLog``."""
    log = _get_owned_log(request, pk)
    return render(request, "medications/medication_log_detail.html", {"log": log})


@login_required
def medication_log_edit_view(request: HttpRequest, pk: int) -> HttpResponse:
    """Render and process the medication-log edit form."""
    log = _get_owned_log(request, pk)

    if request.method == "POST":
        form = MedicationLogEditForm(request.POST)
        if form.is_valid():
            form.apply(log)
            return redirect("medication_log_detail", pk=log.pk)
    else:
        form = MedicationLogEditForm(initial=MedicationLogEditForm.initial_for(log))

    return render(request, "medications/medication_log_edit.html", {"form": form, "log": log})


@login_required
def medication_log_delete_view(request: HttpRequest, pk: int) -> HttpResponse:
    """Render the delete-confirmation page and handle the deletion."""
    log = _get_owned_log(request, pk)
    if request.method == "POST":
        log.delete()
        return redirect("activity_list")
    return render(request, "medications/medication_log_delete.html", {"log": log})
