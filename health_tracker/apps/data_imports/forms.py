"""Forms for the data-import admin tool."""

from __future__ import annotations

from django import forms

from health_tracker.apps.data_imports.utils import (
    MAX_UPLOAD_BYTES,
    ImportResult,
    parse_csv,
    persist,
)
from health_tracker.apps.users.models import User


class CSVImportForm(forms.Form):
    """Upload form for backfilling existing health data via CSV.

    The form validates the uploaded file at the boundary
    (``clean_csv_file``) and exposes :meth:`import_data` as the single
    entry point for "given these inputs, produce the answer." The view
    layer only orchestrates the request/response cycle.
    """

    patient = forms.ModelChoiceField(
        queryset=User.objects.filter(role=User.Role.PATIENT).order_by("username"),
        label="Patient",
    )
    csv_file = forms.FileField(
        label="CSV file",
        help_text=(
            "Required columns: activity_type, created_at. "
            "Optional columns: systolic, diastolic, heart_rate, weight_kg, "
            "spo2, volume_ml, medication_id, notes."
        ),
    )

    def clean_csv_file(self) -> bytes:
        """Validate the upload's size and extension, return its bytes.

        Returns:
            The raw CSV file contents.

        Raises:
            forms.ValidationError: When the file exceeds the size limit
                or does not have a ``.csv`` extension.
        """
        uploaded = self.cleaned_data["csv_file"]
        if uploaded.size > MAX_UPLOAD_BYTES:
            raise forms.ValidationError("CSV file must not exceed 5 MB.")
        name = (uploaded.name or "").lower()
        if not name.endswith(".csv"):
            raise forms.ValidationError("Only .csv files are accepted.")
        return uploaded.read()

    def import_data(self) -> ImportResult:
        """Parse and persist the uploaded CSV.

        Returns an :class:`ImportResult` describing what was created or,
        on any validation error, the list of per-row error messages
        (in which case nothing is persisted).
        """
        patient: User = self.cleaned_data["patient"]
        file_bytes: bytes = self.cleaned_data["csv_file"]
        parsed, errors = parse_csv(file_bytes, patient)
        if errors:
            return ImportResult(errors=errors)
        metric_count, water_count, medication_log_count = persist(parsed)
        return ImportResult(
            metric_count=metric_count,
            water_count=water_count,
            medication_log_count=medication_log_count,
        )
