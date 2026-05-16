"""Tests for the documents app forms."""

from __future__ import annotations

from io import BytesIO
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from health_tracker.apps.documents.forms import DocumentUploadForm


def _make_upload(content: bytes, content_type: str, name: str = "doc.pdf") -> SimpleUploadedFile:
    """Build a SimpleUploadedFile with the requested content type."""
    return SimpleUploadedFile(name, content, content_type=content_type)


class DocumentUploadFormTests(TestCase):
    """Tests for :class:`DocumentUploadForm`."""

    def test_accepts_pdf(self) -> None:
        form = DocumentUploadForm(
            data={"title": "Lab", "notes": ""},
            files={"file": _make_upload(b"hello", "application/pdf")},
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_accepts_jpeg(self) -> None:
        form = DocumentUploadForm(
            data={"title": "Scan", "notes": ""},
            files={"file": _make_upload(b"hello", "image/jpeg", name="s.jpg")},
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_rejects_disallowed_mime_type(self) -> None:
        form = DocumentUploadForm(
            data={"title": "Script", "notes": ""},
            files={"file": _make_upload(b"echo", "application/x-sh", name="s.sh")},
        )
        self.assertFalse(form.is_valid())
        self.assertIn("file", form.errors)

    def test_rejects_oversize_file(self) -> None:
        big_payload = BytesIO(b"a" * (11 * 1024 * 1024))
        upload = SimpleUploadedFile(
            "big.pdf",
            big_payload.getvalue(),
            content_type="application/pdf",
        )
        with patch.object(upload, "size", 11 * 1024 * 1024):
            form = DocumentUploadForm(
                data={"title": "Big", "notes": ""},
                files={"file": upload},
            )
            self.assertFalse(form.is_valid())
            self.assertIn("file", form.errors)
