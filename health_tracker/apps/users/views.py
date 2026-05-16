"""Views for the users app: login and logout."""

from __future__ import annotations

from django.contrib.auth import authenticate
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render

from health_tracker.apps.users.forms import LoginForm


def login_view(request: HttpRequest) -> HttpResponse:
    """Render and process the PIN login form.

    GET renders a blank ``LoginForm``. POST binds the form, authenticates
    via the PIN backend, and on success logs the user in and redirects
    to ``/``. On failure a generic non-field error is added.

    Args:
        request: The incoming HTTP request.

    Returns:
        The rendered login template, or a redirect on success.
    """
    if request.user.is_authenticated:
        return redirect("/")

    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            user = authenticate(
                request,
                username=form.cleaned_data["username"],
                pin=form.cleaned_data["pin"],
            )
            if user is not None:
                auth_login(request, user)
                return redirect("/")
            form.add_error(None, "Nama pengguna atau PIN salah.")
    else:
        form = LoginForm()

    return render(request, "users/login.html", {"form": form})


def logout_view(request: HttpRequest) -> HttpResponse:
    """Log the user out (POST only) and redirect to the login page.

    On GET, redirect silently to ``/`` rather than raising 405. This
    keeps accidental navigation safe.

    Args:
        request: The incoming HTTP request.

    Returns:
        A redirect response.
    """
    if request.method != "POST":
        return redirect("/")
    auth_logout(request)
    return redirect("/login/")
