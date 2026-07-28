"""
Minimal CORS support for the public API (#1268), scoped to ``/api/`` only.

The API is read-only and serves data that's already public, so a permissive
``Access-Control-Allow-Origin: *`` is safe and lets a client-side widget (e.g. a
"recent publications" list on an external academic page) fetch it directly from
the browser. We deliberately don't pull in ``django-cors-headers`` for this --
the surface is one GET-only path prefix.

Only the ``/api/`` prefix gets these headers; the rest of the site is untouched
(no cross-origin exposure of admin, forms, etc.).
"""

API_PREFIX = "/api/"


class ApiCorsMiddleware:
    """Add permissive CORS headers to ``/api/`` responses and answer preflight.

    A browser preflights a cross-origin request with ``OPTIONS``; we short-
    circuit that with a 200 + the CORS headers so the real GET is allowed.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        is_api = request.path.startswith(API_PREFIX)

        if is_api and request.method == "OPTIONS":
            from django.http import HttpResponse

            response = HttpResponse(status=200)
        else:
            response = self.get_response(request)

        if is_api:
            response["Access-Control-Allow-Origin"] = "*"
            response["Access-Control-Allow-Methods"] = "GET, HEAD, OPTIONS"
            response["Access-Control-Allow-Headers"] = "Accept, Content-Type"
            response["Access-Control-Max-Age"] = "86400"

        return response
