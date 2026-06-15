"""
Sitemap classes that power the dynamic ``/sitemap.xml`` (issue #1252).

Django's ``django.contrib.sitemaps`` framework builds the XML on every request
straight from our querysets, so the sitemap is always current — no static file
to regenerate when content changes.

Domain handling: we do NOT use ``django.contrib.sites``. When it isn't
installed, the framework falls back to ``RequestSite``, which takes the domain
from the incoming request host. That means the same code emits
``makeabilitylab.cs.washington.edu`` in prod, ``makeabilitylab-test...`` on the
test server, and ``localhost`` in dev — no per-environment configuration.

We map only the pages that have real, indexable URLs:
  - static listing pages (home, people, publications, projects, awards, news)
  - one entry per visible Project        -> /project/<short_name>/
  - one entry per public Person          -> /member/<url_name>/
  - one entry per News item              -> /news/<slug>/

Publications have no per-publication detail page (only the ``/publications/``
listing), so they are covered by the static sitemap and not enumerated here.
"""

from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from website.models import Project, Person, News


class _HttpsSitemap(Sitemap):
    """
    Base sitemap that pins generated URLs to the https scheme.

    Apache terminates TLS and proxies to Django over plain HTTP, so the
    request scheme Django sees is ``http``. Without this, RequestSite would
    emit ``http://`` <loc> URLs that only 302-redirect to https — making the
    sitemap advertise non-canonical URLs with an extra hop. Pinning the
    protocol here makes every sitemap list the canonical https URLs directly.
    (Cosmetic only in local dev, where the site is served over http.)
    """

    protocol = "https"


class StaticViewSitemap(_HttpsSitemap):
    """Top-level listing pages that aren't tied to a single model instance."""

    changefreq = "weekly"
    priority = 0.8

    def items(self):
        # URL names (in the ``website`` namespace) for the public landing pages.
        return [
            "website:index",
            "website:people",
            "website:publications",
            "website:projects",
            "website:awards",
            "website:news_listing",
        ]

    def location(self, item):
        return reverse(item)


class ProjectSitemap(_HttpsSitemap):
    """Public project pages: /project/<short_name>/."""

    changefreq = "weekly"
    priority = 0.7

    def items(self):
        # Mirror the project view's visibility rule: only is_visible projects
        # are reachable by the public. Explicit ordering keeps sitemap
        # pagination stable (avoids UnorderedObjectListWarning).
        return Project.objects.filter(is_visible=True).order_by("short_name")

    def location(self, obj):
        # The project view resolves short_name (see website/views/project.py).
        return reverse("website:project", args=[obj.short_name])

    def lastmod(self, obj):
        # auto_now DateField, updated on every save.
        return obj.updated


class PersonSitemap(_HttpsSitemap):
    """Public people pages: /member/<url_name>/."""

    changefreq = "monthly"
    priority = 0.6

    def items(self):
        # Anyone who has held a position appears on the /people/ page and has a
        # public member page. Exclude the 'placeholder' default url_name (people
        # whose url_name was never generated) since those won't resolve.
        return (
            Person.objects.filter(position__isnull=False)
            .exclude(url_name="placeholder")
            .order_by("url_name")
            .distinct()
        )

    def location(self, obj):
        return reverse("website:member_by_name", args=[obj.url_name])

    def lastmod(self, obj):
        # May be None for people whose bio was never edited; the framework
        # simply omits <lastmod> in that case.
        return obj.bio_datetime_modified


class NewsSitemap(_HttpsSitemap):
    """News item pages: /news/<slug>/."""

    changefreq = "monthly"
    priority = 0.5

    def items(self):
        return News.objects.exclude(slug__isnull=True)

    def location(self, obj):
        return reverse("website:news_item_by_slug", args=[obj.slug])

    def lastmod(self, obj):
        return obj.date


# Registry passed to django.contrib.sitemaps.views.sitemap in the root URLconf.
sitemaps = {
    "static": StaticViewSitemap,
    "projects": ProjectSitemap,
    "people": PersonSitemap,
    "news": NewsSitemap,
}
