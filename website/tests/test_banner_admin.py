"""
Regression tests for the Banner admin list-management tooling (#1082).

With ~200 banners on production, the changelist gained a visual thumbnail,
right-sidebar filters (including a custom media-type filter), inline toggles,
and bulk actions. These tests pin the pieces that carry logic — the thumbnail
renderer and the media-type filter — plus the static admin configuration the
features depend on.
"""

from website.models import Banner
from website.admin.admin_site import ml_admin_site
from website.admin.banner_admin import BannerAdmin, MediaTypeFilter
from website.tests.base import DatabaseTestCase


class BannerAdminThumbnailTests(DatabaseTestCase):
    """BannerAdmin.thumbnail() renders the right cell for each media state."""

    def setUp(self):
        self.admin = BannerAdmin(Banner, ml_admin_site)

    def test_no_media_renders_dash(self):
        banner = Banner.objects.create(title="Empty")
        self.assertIn('—', self.admin.thumbnail(banner))

    def test_video_only_renders_video_indicator(self):
        banner = Banner.objects.create(
            title="Video", video='banner/videos/clip.mp4')
        self.assertIn('video', self.admin.thumbnail(banner).lower())


class BannerMediaTypeFilterTests(DatabaseTestCase):
    """MediaTypeFilter.filter_queryset partitions banners by media."""

    def setUp(self):
        self.image_banner = Banner.objects.create(
            title="Image", image='banner/pic.jpg')
        self.video_banner = Banner.objects.create(
            title="Video", video='banner/videos/clip.mp4')
        self.empty_banner = Banner.objects.create(title="Empty")

    def _filtered(self, value):
        return set(MediaTypeFilter.filter_queryset(Banner.objects.all(), value))

    def test_image_filter(self):
        self.assertEqual(self._filtered('image'), {self.image_banner})

    def test_video_filter(self):
        self.assertEqual(self._filtered('video'), {self.video_banner})

    def test_none_filter(self):
        self.assertEqual(self._filtered('none'), {self.empty_banner})

    def test_no_value_returns_all(self):
        self.assertEqual(
            self._filtered(None),
            {self.image_banner, self.video_banner, self.empty_banner},
        )


class BannerAdminConfigTests(DatabaseTestCase):
    """The list page exposes the search/filter/inline-edit tooling from #1082."""

    def test_changelist_tooling_configured(self):
        admin = BannerAdmin(Banner, ml_admin_site)
        self.assertEqual(admin.date_hierarchy, 'date_added')
        self.assertIn(MediaTypeFilter, admin.list_filter)
        self.assertIn('project__name', admin.search_fields)
        self.assertEqual(set(admin.list_editable), {'landing_page', 'favorite'})
        # list_editable fields must not be the row link, or Django errors.
        self.assertNotIn('title', admin.list_editable)
        self.assertIn('title', admin.list_display_links)
