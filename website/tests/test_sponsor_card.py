"""
Regression tests for sponsor logo links on the home page.

The sponsor card wrapped its logo in ``<a href="{{ sponsor.url }}">``. Because
``Sponsor.url`` is a nullable ``URLField``, a sponsor with a logo but no URL
rendered ``href="None"`` — Django renders a resolved ``None`` as the literal
string ``"None"`` — which the browser resolves to ``/None``, a crawlable 404
(an SEO bug flagged for Amazon Catalyst / CloudBank). The template now only
emits the anchor when a URL is present. See website/templates/website/index.html.
"""

from django.urls import reverse

from website.models import Sponsor
from website.tests.base import DatabaseTestCase
from website.tests.factories import image_upload


class SponsorCardLinkTests(DatabaseTestCase):
    def _make_sponsor(self, name, url):
        # An icon is required: the card only renders the logo (and its link)
        # inside {% if sponsor.icon %}. icon_cropping gets a valid box so the
        # {% thumbnail %} tag has something to crop.
        return Sponsor.objects.create(
            name=name, url=url,
            icon=image_upload(f"{name.lower()}.gif"),
            icon_cropping="0,0,1,1",
        )

    def test_url_less_sponsor_emits_no_none_link(self):
        self._make_sponsor("CloudBank", url=None)
        resp = self.client.get(reverse("website:index"))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        self.assertNotIn('href="None"', html)
        self.assertNotIn("/None", html)

    def test_sponsor_with_url_is_still_linked(self):
        self._make_sponsor("NSF", url="https://www.nsf.gov")
        resp = self.client.get(reverse("website:index"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'href="https://www.nsf.gov"')
