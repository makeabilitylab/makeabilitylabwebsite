"""Helpers for admin login throttling (django-axes). See the AXES_* block in settings.py."""
from django.contrib.auth import get_user_model
from django.utils.crypto import salted_hmac

# Prefix of what axes records in place of a username that matches no account.
# Real usernames cannot contain spaces or parentheses, so the two never collide.
UNKNOWN_PREFIX = "(unknown) "


def get_throttle_username(request, credentials=None):
    """Return the username axes should count a login attempt against.

    Wired in as ``AXES_USERNAME_CALLABLE``; axes calls it with the request and,
    when it has them, the credentials passed to ``authenticate()``.

    A name that matches a real account is returned unchanged. Anything else is
    replaced by ``"(unknown) "`` plus a short keyed hash of what was typed,
    because people sometimes type their password into the username box, axes
    stores the username in plain text, and the nightly database dump would
    keep it.

    Each unknown name gets its OWN hash, and so its own failure count, on
    purpose. If all unknown names shared one counter, that counter would lock
    after a few junk guesses, and from then on a made-up name would be refused
    at once while a real one would not: a way to test which usernames exist.

    Example::

        get_throttle_username(request, {"username": "jonfroehlich"})  # "jonfroehlich"
        get_throttle_username(request, {"username": "hunter2"})       # "(unknown) 3f9a0c..."
    """
    username = None
    if isinstance(credentials, dict):
        username = credentials.get("username")
    if username is None and request is not None:
        username = request.POST.get("username")
    if not username or not isinstance(username, str):
        return username
    User = get_user_model()
    if User.objects.filter(**{User.USERNAME_FIELD: username}).exists():
        return username
    digest = salted_hmac("website.login_throttle.unknown", username).hexdigest()[:16]
    return UNKNOWN_PREFIX + digest
