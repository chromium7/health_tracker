"""Constants for the documents app."""

from __future__ import annotations

ALLOWED_MIME_TYPES: frozenset[str] = frozenset(
    {
        "application/pdf",
        "image/jpeg",
        "image/png",
    }
)

MAX_UPLOAD_BYTES: int = 10 * 1024 * 1024
