"""Patient-uploaded document model."""

from __future__ import annotations

from django.db import models

from health_tracker.apps.users.models import User


class Document(models.Model):
    """A patient-uploaded medical file (lab result, prescription, etc.).

    Allowed file types are enforced in
    :class:`~health_tracker.apps.documents.forms.DocumentUploadForm`:
    PDF, JPG, PNG, with a 10 MB maximum.

    Attributes:
        patient: The patient this document belongs to.
        title: Human-readable label for the document.
        notes: Optional free-text context.
        file: The uploaded file.
        uploaded_at: Timestamp set automatically on creation.
    """

    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name="documents")
    title = models.CharField(max_length=200)
    notes = models.TextField(blank=True)
    file = models.FileField(upload_to="patient_documents/%Y/%m/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self) -> str:
        return self.title
