"""
Serves /robots.txt dynamically (issue #1252).

We serve this from Django (not as a static file at the web-server root) because
the maintainer has no web-server access — routing it through a view is the only
control we have, and it lets us vary behavior by environment.

Two behaviors:
  - PROD: allow crawling and advertise the sitemap.
  - Everything else (notably the TEST server, DJANGO_ENV=TEST): disallow all
    crawling so the test site is never indexed and can't compete with the
    production site in search results.

The sitemap URL is built from the request host, so it points at whatever domain
the request came in on (prod / test / localhost).
"""

import os

from django.http import HttpResponse


def robots_txt(request):
    """Return an environment-appropriate robots.txt as text/plain."""
    sitemap_url = request.build_absolute_uri("/sitemap.xml")

    if os.environ.get("DJANGO_ENV") == "PROD":
        lines = [
            "User-agent: *",
            "Allow: /",
            "",
            f"Sitemap: {sitemap_url}",
        ]
    else:
        # Test / dev: keep the whole site out of search indexes.
        lines = [
            "User-agent: *",
            "Disallow: /",
        ]

    return HttpResponse("\n".join(lines) + "\n", content_type="text/plain")
