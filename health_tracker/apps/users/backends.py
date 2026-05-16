"""PIN-based authentication backend for HealthTracker.

Replaces Django's password backend with a backend that authenticates a
user by ``(username, pin)`` pair stored directly on the User row.
"""

from __future__ import annotations

from django.contrib.auth.backends import BaseBackend
from django.http import HttpRequest

from health_tracker.apps.users.models import User


class PINAuthBackend(BaseBackend):
    """Authenticate users via a 4-digit PIN instead of a password.

    NOTE: This backend bypasses Django's password hashing entirely. PINs
    are compared as plaintext against ``User.pin``.

    TODO (production): store PINs hashed via
    ``django.contrib.auth.hashers.make_password`` and verify with
    ``check_password`` rather than as plaintext.
    """

    def authenticate(
        self,
        request: HttpRequest | None,
        username: str | None = None,
        pin: str | None = None,
    ) -> User | None:
        """Return the matching active user when ``(username, pin)`` are valid.

        Args:
            request: The current request, or ``None`` when called outside
                a request lifecycle.
            username: Submitted username.
            pin: Submitted 4-digit PIN.

        Returns:
            The authenticated ``User`` on success, or ``None`` on any
            failure (missing input, unknown username, wrong PIN,
            inactive account).
        """
        if not username or not pin:
            return None
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return None
        if user.pin == pin and user.is_active:
            return user
        return None

    def get_user(self, user_id: int) -> User | None:
        """Fetch a user by primary key for the session middleware.

        Args:
            user_id: Primary key stored in the session.

        Returns:
            The ``User`` instance, or ``None`` if no such row exists.
        """
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
