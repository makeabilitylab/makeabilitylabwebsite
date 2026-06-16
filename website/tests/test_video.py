"""Tests for Video model methods."""

from datetime import date, timedelta

from django.test import SimpleTestCase


class VideoAgeTests(SimpleTestCase):
    """
    Regression tests for Video.get_age_in_ms (relates to #1091).

    The method computed `datetime.now().date() - self.date`, which raised
    TypeError when the nullable `date` field was None. It now returns None
    for a dateless video so video-age.js falls back to the static date.
    Pure unit tests: Video instances are constructed but never saved.
    """

    def test_none_date_returns_none(self):
        from website.models import Video
        self.assertIsNone(Video(date=None).get_age_in_ms())

    def test_past_date_returns_positive_int(self):
        from website.models import Video
        age = Video(date=date.today() - timedelta(days=7)).get_age_in_ms()
        self.assertIsInstance(age, int)
        # 7 days in ms, allowing slack for the now() call crossing midnight.
        self.assertGreaterEqual(age, 6 * 24 * 60 * 60 * 1000)

    def test_today_is_below_one_day(self):
        # A video published today must yield an age below one day in ms. This
        # is the contract video-age.js relies on to render "Today" instead of
        # "0 seconds ago" (issue #1091); pin it server-side since the JS guard
        # itself has no test runner in this repo.
        from website.models import Video
        one_day_ms = 24 * 60 * 60 * 1000
        age = Video(date=date.today()).get_age_in_ms()
        self.assertIsInstance(age, int)
        self.assertGreaterEqual(age, 0)
        self.assertLess(age, one_day_ms)

    def test_future_date_returns_negative_int(self):
        from website.models import Video
        age = Video(date=date.today() + timedelta(days=7)).get_age_in_ms()
        self.assertIsInstance(age, int)
        self.assertLess(age, 0)
