"""Tests for the documents app views."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from health_tracker.apps.documents.models import Document
from health_tracker.apps.users.models import User

_MEDIA_ROOT = tempfile.mkdtemp(prefix="ht-test-media-")


@override_settings(MEDIA_ROOT=_MEDIA_ROOT)
class DocumentViewsTests(TestCase):
    """Tests for the documents list and upload views."""

    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(_MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def setUp(self) -> None:
        self.client = Client()
        self.patient = User.objects.create(
            username="pat",
            pin="0000",
            role=User.Role.PATIENT,
        )

    def test_list_requires_login(self) -> None:
        response = self.client.get(reverse("document_list"))
        self.assertEqual(response.status_code, 302)

    def test_list_shows_only_my_documents(self) -> None:
        other = User.objects.create(
            username="other",
            pin="0000",
            role=User.Role.PATIENT,
        )
        Document.objects.create(
            patient=other,
            title="Not yours",
            file=SimpleUploadedFile("other.pdf", b"data", "application/pdf"),
        )
        Document.objects.create(
            patient=self.patient,
            title="Mine",
            file=SimpleUploadedFile("mine.pdf", b"data", "application/pdf"),
        )
        self.client.force_login(self.patient)
        response = self.client.get(reverse("document_list"))
        self.assertContains(response, "Mine")
        self.assertNotContains(response, "Not yours")

    def test_upload_creates_document_for_patient(self) -> None:
        self.client.force_login(self.patient)
        upload = SimpleUploadedFile(
            "report.pdf",
            b"hello",
            content_type="application/pdf",
        )
        response = self.client.post(
            reverse("document_upload"),
            data={"title": "Report", "notes": "Lab work", "file": upload},
        )
        self.assertRedirects(
            response,
            reverse("document_list"),
            fetch_redirect_response=False,
        )
        document = Document.objects.get(title="Report")
        self.assertEqual(document.patient, self.patient)
        self.assertTrue(Path(document.file.path).exists())

    def test_upload_rejects_disallowed_mime_type(self) -> None:
        self.client.force_login(self.patient)
        upload = SimpleUploadedFile(
            "bad.sh",
            b"data",
            content_type="application/x-sh",
        )
        response = self.client.post(
            reverse("document_upload"),
            data={"title": "Bad", "notes": "", "file": upload},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Document.objects.exists())
