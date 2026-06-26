"""Tests for website.views.serve_pdf."""

from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from website.models import Publication
from website.tests.base import DatabaseTestCase


def _miss_original_fallback(mock_pub):
    """Stub the #1401 original_pdf_filename fallback chain
    (``filter(...).exclude(...).exclude(...).first()``) to miss, so tests
    exercising the exact/fuzzy/404 paths fall through it as before."""
    qs = mock_pub.objects.filter.return_value
    qs.exclude.return_value.exclude.return_value.first.return_value = None


class ServePdfTests(SimpleTestCase):
    """
    Regression tests for website.views.serve_pdf.

    The previous implementation used
        Publication.objects.get(pdf_file__icontains=filename)
    which had two failure modes:

    1. Only ``ObjectDoesNotExist`` was caught. When a substring matched
       multiple publications' stored paths, ``MultipleObjectsReturned``
       was raised and propagated as a 500 — e.g. requesting "Speech"
       when both "Froehlich2010Speech.pdf" and
       "Froehlich2010Speechalytics.pdf" exist.
    2. ``__icontains`` is a substring match (SQL ``LIKE %x%``), so a
       probe for ".pdf" matched every PDF in the database. Combined with
       the fuzzy difflib fallback that redirects on miss, this enabled
       enumeration of stored filenames.

    The fix uses ``filter(pdf_file__iendswith=filename).first()`` for
    the exact branch: ``.first()`` can't raise ``MultipleObjectsReturned``,
    and ``__iendswith`` only matches paths ending in the requested name.
    The fuzzy difflib fallback is retained for academic-link integrity
    and is only invoked on actual miss.
    """

    def test_exact_match_returns_pdf_response(self):
        """Happy path: an exact filename match returns the PDF inline."""
        from website.views.serve_pdf import serve_pdf
        fake_pub = MagicMock()
        fake_pub.pdf_file.read.return_value = b"%PDF-1.4 fake"
        fake_pub.pdf_file.name = "publications/Froehlich2018Speech.pdf"
        with patch("website.views.serve_pdf.Publication") as MockPub:
            MockPub.objects.filter.return_value.first.return_value = fake_pub
            response = serve_pdf(MagicMock(), "Froehlich2018Speech.pdf")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")

    def test_uses_iendswith_not_icontains(self):
        """
        Regression for the substring-probe enumeration bug. The exact
        branch must use ``__iendswith``; a request for ".pdf" must
        therefore miss (since no pub's path equals ".pdf") rather than
        matching every pub via substring.
        """
        from django.http import Http404
        from website.views.serve_pdf import serve_pdf
        with patch("website.views.serve_pdf.Publication") as MockPub, patch(
            "website.views.serve_pdf.get_closest_filename_from_database",
            return_value=None,
        ):
            MockPub.objects.filter.return_value.first.return_value = None
            _miss_original_fallback(MockPub)
            with self.assertRaises(Http404):
                serve_pdf(MagicMock(), ".pdf")
            # assert_any_call (not assert_called_with): the original-filename
            # fallback issues a later filter() call, so the iendswith call is
            # no longer the most recent one.
            MockPub.objects.filter.assert_any_call(pdf_file__iendswith=".pdf")

    def test_no_exact_match_uses_fuzzy_redirect(self):
        """
        Stale-external-link preservation. When the exact branch misses,
        the difflib fallback should redirect to the closest filename it
        finds. This is the academic-link-integrity feature.
        """
        from website.views.serve_pdf import serve_pdf
        with patch("website.views.serve_pdf.Publication") as MockPub, patch(
            "website.views.serve_pdf.get_closest_filename_from_database",
            return_value="publications/Froehlich2018Updated.pdf",
        ):
            MockPub.objects.filter.return_value.first.return_value = None
            _miss_original_fallback(MockPub)
            response = serve_pdf(MagicMock(), "Froehlich2018Old.pdf")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/media/publications/Froehlich2018Updated.pdf")

    def test_no_exact_no_fuzzy_returns_404(self):
        """If neither the exact branch nor the fuzzy fallback finds anything, 404."""
        from django.http import Http404
        from website.views.serve_pdf import serve_pdf
        with patch("website.views.serve_pdf.Publication") as MockPub, patch(
            "website.views.serve_pdf.get_closest_filename_from_database",
            return_value=None,
        ):
            MockPub.objects.filter.return_value.first.return_value = None
            _miss_original_fallback(MockPub)
            with self.assertRaises(Http404):
                serve_pdf(MagicMock(), "NoSuchPaper.pdf")


class ServePdfOriginalFilenameFallbackTests(DatabaseTestCase):
    """
    DB-backed test for the #1401 original_pdf_filename fallback: after a
    publication PDF is re-standardized, a stale external link to its old
    (original upload) filename must still resolve. serve_pdf matches the
    requested name against the captured ``original_pdf_filename`` and redirects
    to the current file — an exact resolution, before the difflib guess.
    """

    def test_old_filename_redirects_to_current_via_original_pdf_filename(self):
        from website.views.serve_pdf import serve_pdf
        pub = self.make_publication(title="Gamifying Green", year=2013)
        # Simulate a re-standardized pub: current file is the standardized
        # name; the old upload name is preserved in original_pdf_filename.
        Publication.objects.filter(pk=pub.pk).update(
            pdf_file="publications/Froehlich_GamifyingGreen_CHI2013.pdf",
            original_pdf_filename="Gamifying_Green_yY7Jx99.pdf",
        )

        response = serve_pdf(MagicMock(), "Gamifying_Green_yY7Jx99.pdf")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.url,
            "/media/publications/Froehlich_GamifyingGreen_CHI2013.pdf",
        )
