"""Admin-only views for importing existing health data from CSV."""

from __future__ import annotations

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse

from health_tracker.apps.data_imports.forms import CSVImportForm
from health_tracker.apps.data_imports.utils import ACTIVITY_CHOICES, CSV_COLUMNS


@staff_member_required
def csv_import_view(request: HttpRequest) -> HttpResponse:
    """Render and process the admin CSV import form.

    On POST the form parses the CSV, validates every row, and persists
    the records atomically. Any row error aborts the whole import and
    the errors are re-rendered with the form.

    Args:
        request: The incoming HTTP request.

    Returns:
        The rendered form on GET / invalid POST / per-row errors, or a
        redirect back to the admin index on a successful import.
    """
    if request.method == "POST":
        form = CSVImportForm(request.POST, request.FILES)
        if form.is_valid():
            result = form.import_data()
            if result.success:
                messages.success(
                    request,
                    (
                        f"Imported {result.total_created} record(s): "
                        f"{result.metric_count} metric(s), "
                        f"{result.water_count} water log(s), "
                        f"{result.medication_log_count} medication log(s)."
                    ),
                )
                return redirect(reverse("admin:index"))
            row_errors = result.errors
        else:
            row_errors = []
    else:
        form = CSVImportForm()
        row_errors = []

    context = {
        "form": form,
        "row_errors": row_errors,
        "activity_choices": ACTIVITY_CHOICES,
        "csv_columns": CSV_COLUMNS,
        "title": "Import data from CSV",
    }
    return render(request, "admin/data_imports/csv_import.html", context)
