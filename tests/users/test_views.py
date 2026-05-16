"""Tests for the users app views: login and logout."""

from __future__ import annotations

from django.test import Client, TestCase
from django.urls import reverse

from health_tracker.apps.users.models import User


class LoginViewTests(TestCase):
    """Behavioural tests for :func:`login_view`."""

    def setUp(self) -> None:
        self.client = Client()
        self.user = User.objects.create(
            username="alice",
            pin="1234",
            role=User.Role.PATIENT,
        )

    def test_get_renders_form(self) -> None:
        response = self.client.get(reverse("login"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="username"')
        self.assertContains(response, 'name="pin"')

    def test_post_with_valid_credentials_logs_in(self) -> None:
        response = self.client.post(
            reverse("login"),
            data={"username": "alice", "pin": "1234"},
        )
        self.assertRedirects(response, "/", fetch_redirect_response=False)
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.user.pk)

    def test_post_with_invalid_credentials_shows_generic_error(self) -> None:
        response = self.client.post(
            reverse("login"),
            data={"username": "alice", "pin": "9999"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Nama pengguna atau PIN salah.")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_post_with_non_digit_pin_rejected(self) -> None:
        response = self.client.post(
            reverse("login"),
            data={"username": "alice", "pin": "abcd"},
        )
        self.assertEqual(response.status_code, 200)
        # The login template intentionally hides field-level errors to
        # avoid leaking which field was wrong (Section 10.8). What we
        # care about is that the form was rejected and no session was
        # created.
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertIn("pin", response.context["form"].errors)


class LogoutViewTests(TestCase):
    """Behavioural tests for :func:`logout_view`."""

    def setUp(self) -> None:
        self.client = Client()
        self.user = User.objects.create(
            username="alice",
            pin="1234",
            role=User.Role.PATIENT,
        )

    def test_get_redirects_to_root(self) -> None:
        response = self.client.get(reverse("logout"))
        self.assertRedirects(response, "/", fetch_redirect_response=False)

    def test_post_logs_user_out_and_redirects(self) -> None:
        self.client.force_login(self.user)
        response = self.client.post(reverse("logout"))
        self.assertRedirects(response, "/login/", fetch_redirect_response=False)
        self.assertNotIn("_auth_user_id", self.client.session)
