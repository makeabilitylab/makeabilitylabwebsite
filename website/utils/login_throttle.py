"""Helpers for admin login throttling (django-axes). See the AXES_* block in settings.py."""
from django.contrib.auth import get_user_model

# What axes records in place of a username that matches no account.
UNKNOWN_USERNAME = "(unknown username)"


def get_throttle_username(request, credentials=None):
    """Return the username axes should count a login attempt against.

    Wired in as ``AXES_USERNAME_CALLABLE``; axes calls it with the request and,
    when it has them, the credentials passed to ``authenticate()``.

    A name that matches a real account is returned unchanged, so each account
    has its own failure count. Anything else is replaced by ``UNKNOWN_USERNAME``,
    for two reasons:

    - People sometimes type their password into the username box. Axes stores
      the username in plain text, and the nightly database dump would keep it.
    - Bots guess thousands of names (``admin``, ``root``, ...). Sharing one
      counter keeps that to a handful of rows instead of one per name.

    Example::

        get_throttle_username(request, {"username": "jonfroehlich"})  # "jonfroehlich"
        get_throttle_username(request, {"username": "hunter2"})       # "(unknown username)"
    """
    username = (credentials or {}).get("username")
    if username is None:
        username = request.POST.get("username")
    if not username:
        return username
    User = get_user_model()
    if User.objects.filter(**{User.USERNAME_FIELD: username}).exists():
        return username
    return UNKNOWN_USERNAME
