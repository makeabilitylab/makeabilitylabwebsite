"""Unit tests for website.utils.timeutils (#1278, item 5).

Pure functions, zero DB. These had no coverage despite feeding user-facing
strings (duration labels) and the forum-name / url-name cleaning pipeline
(ends_with_year / remove_trailing_year are used by clean_forum_name and the
url_name de-collision logic).
"""

from datetime import timedelta

from django.test import SimpleTestCase

from website.utils.timeutils import (
    ends_with_year,
    humanize_duration,
    remove_trailing_year,
)


class HumanizeDurationTests(SimpleTestCase):
    """humanize_duration picks the largest fitting unit (year/month/week/day)."""

    def test_years_bucket(self):
        self.assertEqual(humanize_duration(timedelta(days=365)), "1.0 years")
        self.assertEqual(humanize_duration(timedelta(days=730)), "2.0 years")

    def test_months_bucket(self):
        self.assertEqual(humanize_duration(timedelta(days=60)), "2.0 months")

    def test_weeks_bucket(self):
        self.assertEqual(humanize_duration(timedelta(days=14)), "2.0 weeks")

    def test_days_bucket_is_the_sub_week_fallback(self):
        self.assertEqual(humanize_duration(timedelta(days=3)), "3.0 days")

    def test_abbreviated_units(self):
        self.assertEqual(
            humanize_duration(timedelta(days=365), use_abbreviated_units=True),
            "1.0 yrs",
        )

    def test_sig_figs_controls_precision(self):
        self.assertEqual(
            humanize_duration(timedelta(days=400), sig_figs=2), "1.10 years"
        )


class EndsWithYearTests(SimpleTestCase):
    def test_trailing_four_digits_is_a_year(self):
        self.assertTrue(ends_with_year("CHI 2022"))

    def test_no_trailing_digits(self):
        self.assertFalse(ends_with_year("CHI"))

    def test_none_is_false(self):
        self.assertFalse(ends_with_year(None))


class RemoveTrailingYearTests(SimpleTestCase):
    def test_strips_trailing_year_and_whitespace(self):
        self.assertEqual(remove_trailing_year("CHI 2022"), "CHI")

    def test_no_year_returns_input_unchanged(self):
        self.assertEqual(remove_trailing_year("CHI"), "CHI")

    def test_none_returns_empty_string(self):
        self.assertEqual(remove_trailing_year(None), "")
