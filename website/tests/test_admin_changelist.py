"""
Phase 1 admin changelist quick-wins (#1083, from the #1082 admin audit).

Two kinds of coverage:
  1. A regression test for the News changelist thumbnail, which previously had
     no exception guard — a single corrupt/unreadable image would 500 the whole
     list page.
  2. Lightweight config assertions that lock in the search / ordering /
     date_hierarchy added across the content admins, so they can't silently
     regress.
"""

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.test import RequestFactory

from website.models import News, Photo, Keyword
from website.admin.admin_site import ml_admin_site
from website.admin.news_admin import NewsAdmin
from website.admin.keyword_admin import KeywordAdmin
from website.admin.publication_admin import PublicationAdmin
from website.admin.talk_admin import TalkAdmin
from website.admin.poster_admin import PosterAdmin
from website.admin.video_admin import VideoAdmin
from website.admin.grant_admin import GrantAdmin
from website.admin.award_admin import AwardAdmin
from website.admin.project_admin import ProjectAdmin
from website.admin.project_umbrella_admin import ProjectUmbrellaAdmin
from website.admin.photo_admin import PhotoAdmin
from website.admin.position_admin import PositionAdmin
from website.admin.sponsor_admin import SponsorAdmin
from website.tests.base import DatabaseTestCase


class NewsAdminThumbnailRobustnessTests(DatabaseTestCase):
    """A corrupt image must not crash the News changelist (#1082 audit)."""

    def test_corrupt_image_returns_placeholder_instead_of_raising(self):
        news = self.make_news_item(title="Corrupt image news")
        # Write non-image bytes so os.path.isfile() passes (the file exists) but
        # easy_thumbnails raises InvalidImageFormatError when it tries to render.
        news.image.save("not_an_image.jpg",
                        ContentFile(b"definitely not an image"), save=False)
        self.addCleanup(lambda: news.image.delete(save=False))

        admin = NewsAdmin(News, ml_admin_site)
        # Must not raise; the guard returns the same placeholder as the no-image case.
        self.assertEqual(admin.get_display_thumbnail(news), 'No Thumbnail')


class PhotoResolutionRobustnessTests(DatabaseTestCase):
    """A missing/unreadable image file must not crash the Photo changelist (#1346)."""

    def test_missing_file_returns_unknown_instead_of_raising(self):
        # Point the ImageField at a path with no backing file, so reading
        # width/height (which opens the file) raises FileNotFoundError.
        photo = Photo(caption="Ghost photo", picture="projects/images/does_not_exist.jpg")
        # Must not raise; the guard returns a placeholder.
        self.assertEqual(photo.get_resolution_as_str(), 'Unknown')


class AdminChangelistConfigTests(DatabaseTestCase):
    """Lock in the Phase 1 search / ordering / date_hierarchy additions."""

    def test_author_and_venue_search_on_artifacts(self):
        for admin_cls in (PublicationAdmin, TalkAdmin, PosterAdmin):
            self.assertIn('authors__last_name', admin_cls.search_fields,
                          f"{admin_cls.__name__} should be searchable by author")
            self.assertEqual(admin_cls.date_hierarchy, 'date',
                             f"{admin_cls.__name__} should have a date drill-down")

    def test_poster_no_longer_string_searches_date(self):
        self.assertNotIn('date', PosterAdmin.search_fields)
        self.assertEqual(PosterAdmin.ordering, ('-date',))

    def test_video_search_and_hierarchy(self):
        self.assertNotIn('date', VideoAdmin.search_fields)
        self.assertIn('projects__name', VideoAdmin.search_fields)
        self.assertEqual(VideoAdmin.date_hierarchy, 'date')

    def test_grant_searchable_by_person_and_sponsor(self):
        self.assertIn('authors__last_name', GrantAdmin.search_fields)
        self.assertIn('sponsor__name', GrantAdmin.search_fields)
        self.assertNotIn('date', GrantAdmin.search_fields)
        self.assertEqual(GrantAdmin.date_hierarchy, 'date')

    def test_award_date_hierarchy(self):
        self.assertEqual(AwardAdmin.date_hierarchy, 'date')

    def test_news_has_search_and_hierarchy(self):
        self.assertIn('author__last_name', NewsAdmin.search_fields)
        self.assertEqual(NewsAdmin.date_hierarchy, 'date')

    def test_keyword_search_and_ordering(self):
        self.assertEqual(KeywordAdmin.search_fields, ['keyword'])
        self.assertEqual(KeywordAdmin.ordering, ['keyword'])

    def test_project_search_and_ordering(self):
        self.assertIn('project_umbrellas__name', ProjectAdmin.search_fields)
        self.assertEqual(ProjectAdmin.ordering, ('name',))

    def test_project_search_executes(self):
        """Regression for the project changelist search 500: search_fields
        referenced 'keywords__name', but Keyword's field is 'keyword', so any
        admin search raised FieldError ('Unsupported lookup name__icontains for
        ForeignKey'). Exercise the real search query so a bad field path can't
        silently regress. (admin search on /admin/website/project/?q=...)"""
        project = self.make_project(name="Sound Awareness", short_name="soundaware")
        project.keywords.add(Keyword.objects.create(keyword="accessibility"))

        admin = ProjectAdmin(type(project), ml_admin_site)
        request = RequestFactory().get('/admin/website/project/', {'q': 'access'})
        request.user = None
        qs, _ = admin.get_search_results(request, admin.get_queryset(request), 'access')
        # Force SQL evaluation — this is what raised the 500 before the fix.
        self.assertIn(project, list(qs))

    def test_project_umbrella_search_and_ordering(self):
        self.assertEqual(ProjectUmbrellaAdmin.search_fields, ['name', 'short_name'])
        self.assertEqual(ProjectUmbrellaAdmin.ordering, ('name',))

    def test_photo_search(self):
        self.assertIn('project__name', PhotoAdmin.search_fields)

    def test_photo_project_column_and_select_related(self):
        # The owning project is surfaced as a column; select_related keeps the
        # changelist constant-query as rows grow (#1346 Phase 4).
        self.assertIn('project', PhotoAdmin.list_display)
        self.assertEqual(PhotoAdmin.list_select_related, ('project',))

    def test_position_search(self):
        self.assertIn('person__last_name', PositionAdmin.search_fields)

    def test_sponsor_ordering(self):
        self.assertEqual(SponsorAdmin.ordering, ('name',))


class AdminSearchExecutesTests(DatabaseTestCase):
    """Every registered admin's search must actually *run*, not just be declared.

    The project changelist 500'd in prod because search_fields pointed at a
    field path that doesn't exist ('keywords__name' — Keyword's field is
    'keyword'). The older config tests only asserted that search_fields
    *contained* a given string, so they never built the SQL and couldn't catch a
    bad path. This sweep loops over every ModelAdmin registered on the custom
    admin site, runs its search with a benign term, and forces query evaluation
    — turning any invalid field path (FieldError) into a failing test for the
    specific admin, automatically covering admins added in the future.
    """

    @classmethod
    def setUpTestData(cls):
        cls.superuser = get_user_model().objects.create_superuser(
            username="search_sweep_admin", email="sweep@example.com", password="pw")

    def test_all_admin_searches_execute(self):
        rf = RequestFactory()
        checked = []
        for model, model_admin in ml_admin_site._registry.items():
            if not model_admin.search_fields:
                continue
            url = f"/admin/{model._meta.app_label}/{model._meta.model_name}/"
            request = rf.get(url, {"q": "test"})
            request.user = self.superuser
            with self.subTest(admin=type(model_admin).__name__):
                qs, _ = model_admin.get_search_results(
                    request, model_admin.get_queryset(request), "test")
                # Force SQL evaluation — a bad field path raises here, not above.
                list(qs[:1])
            checked.append(type(model_admin).__name__)
        # Guard against the loop silently finding nothing to check.
        self.assertGreater(len(checked), 5)
