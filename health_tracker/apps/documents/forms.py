"""Forms for the documents app."""

from __future__ import annotations

from typing import Any

from django import forms

from health_tracker.apps.documents.models import Document
from health_tracker.apps.documents.utils import ALLOWED_MIME_TYPES, MAX_UPLOAD_BYTES


class DocumentUploadForm(forms.ModelForm):
    """Validate and persist patient document uploads."""

    class Meta:
        model = Document
        fields = ["title", "notes", "file"]

    def clean_file(self) -> Any:
        """Validate the upload's MIME type and size.

        Returns:
            The cleaned uploaded file.

        Raises:
            forms.ValidationError: When the file type is not allowed or
                exceeds the size limit.
        """
        # Production note: replace ``content_type`` (a client-supplied
        # header) with magic-byte inspection via python-magic:
        #     import magic
        #     mime = magic.from_buffer(uploaded.read(2048), mime=True)
        #     uploaded.seek(0)
        # The header is trivially forgeable by a malicious client.
        uploaded = self.cleaned_data["file"]
        if uploaded.content_type not in ALLOWED_MIME_TYPES:
            raise forms.ValidationError("Hanya berkas PDF, JPG, dan PNG yang diterima.")
        if uploaded.size > MAX_UPLOAD_BYTES:
            raise forms.ValidationError("Ukuran berkas tidak boleh melebihi 10 MB.")
        return uploaded
