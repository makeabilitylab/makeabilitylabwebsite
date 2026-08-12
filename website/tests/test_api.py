"""
Integration tests for the public read-only REST API (#1268).

Exercises the real URL/view/serializer stack through Django's test client so the
API contract (endpoints, filters, pagination, visibility gating, absolute URLs,
CORS) is pinned against regressions. Uses the shared DatabaseTestCase fixtures
plus a few direct model creates for the relationships the factories don't cover
(Position, Sponsor/Grant, ProjectRole leadership).
"""

import io
import os
import shutil
import tempfile
from datetime import date
from urllib.parse import unquote, urlparse

from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test import SimpleTestCase, override_settings
from django.test.utils import CaptureQueriesContext
from PIL import Image

from website.api.serializers import (
    API_PERSON_THUMBNAIL_SIZE,
    API_PROJECT_THUMBNAIL_SIZE,
)
from website.models import Grant, Person, Position, ProjectRole, Sponsor
from website.models.person import PERSON_THUMBNAIL_SIZE
from website.models.position import Title
from website.models.project import PROJECT_THUMBNAIL_SIZE
from website.models.project_role import LeadProjectRoleTypes
from website.models.publication import PubType
from website.tests.base import DatabaseTestCase
from website.utils.thumbnail_utils import get_cropped_thumbnail

# The API now generates cropped derivatives (#1432), so these tests write image
# files. Keep them out of the repo's media/ dir, which already holds tens of
# thousands of files left by earlier suites.
_TEST_MEDIA_ROOT = tempfile.mkdtemp(prefix="ml_api_tests_")


def png_upload(name, size=(800, 600), color=(200, 30, 30)):
    """A real (not 1x1) PNG upload, so cropping/resizing has something to do."""
    buffer = io.BytesIO()
    Image.new("RGB", size, color).save(buffer, format="PNG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")


@override_settings(MEDIA_ROOT=_TEST_MEDIA_ROOT)
class ApiTestCase(DatabaseTestCase):
    @classmethod
    def tearDownClass(cls):
        # Subclasses inherit this; rmtree is idempotent and FileSystemStorage
        # recreates directories on demand, so repeated cleanup is harmless.
        shutil.rmtree(_TEST_MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        # A visible project (Project Sidewalk) and a hidden one.
        self.project = self.make_project(
            name="Project Sidewalk", short_name="projectsidewalk", is_visible=True
        )
        self.hidden_project = self.make_project(
            name="Secret Project", short_name="secretproj", is_visible=False
        )

        # Jon is a lab member (has a Position) and PI on the project.
        self.jon = self.make_person(first_name="Jon", last_name="Froehlich")
        Position.objects.create(
            person=self.jon, start_date=date(2012, 1, 1), title=Title.FULL_PROF
        )
        ProjectRole.objects.create(
            person=self.jon,
            project=self.project,
            start_date=date(2012, 1, 1),
            lead_project_role=LeadProjectRoleTypes.PI,
        )
        # Jon also held a *past* (ended) Co-PI role. Even though he's currently
        # an active PI, this past lead role must still surface in leadership --
        # the case Project.get_project_leadership() drops (per-person "inactive").
        ProjectRole.objects.create(
            person=self.jon,
            project=self.project,
            start_date=date(2010, 1, 1),
            end_date=date(2011, 12, 31),
            lead_project_role=LeadProjectRoleTypes.CO_PI,
        )
        # A person who was only ever a past student lead (role ended).
        self.past_lead = self.make_person(first_name="Past", last_name="Lead")
        ProjectRole.objects.create(
            person=self.past_lead,
            project=self.project,
            start_date=date(2013, 1, 1),
            end_date=date(2016, 1, 1),
            lead_project_role=LeadProjectRoleTypes.STUDENT_LEAD,
        )

        # An external co-author with NO Position -> should not appear in /people/.
        self.coauthor = self.make_person(first_name="Ext", last_name="Author")

        # Six conference pubs authored by Jon and attached to the project
        # (years 2018..2023), plus one unrelated journal pub by the co-author.
        self.project_pubs = []
        for year in range(2018, 2024):
            pub = self.make_publication(
                title=f"Sidewalk Paper {year}", year=year, authors=[self.jon]
            )
            pub.projects.add(self.project)
            self.project_pubs.append(pub)

        self.other_pub = self.make_publication(
            title="Unrelated Journal Paper",
            year=2024,
            authors=[self.coauthor],
            pub_venue_type=PubType.JOURNAL,
        )

        # A grant funding the project.
        self.sponsor = Sponsor.objects.create(name="National Science Foundation",
                                               short_name="NSF")
        self.grant = Grant.objects.create(
            title="NSF Award for Sidewalk",
            sponsor=self.sponsor,
            date=date(2015, 1, 1),
            funding_amount=500000,
            grant_id="1302338",
            # UW's internal Workday codes (#1448). Populated here on purpose: the
            # tests below assert they never reach the public payload.
            uw_grant_id="GR012345",
            uw_award_number="AWD-00012345",
            uw_award_name="Internal UW Award Name",
        )
        self.grant.projects.add(self.project)

    # ---- publications list: filtering, ordering, pagination -----------------

    def test_publications_list_returns_all(self):
        resp = self.client.get("/api/v1/publications/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["count"], 7)

    def test_publications_pagination_page_size(self):
        resp = self.client.get("/api/v1/publications/?page_size=5")
        body = resp.json()
        self.assertEqual(body["count"], 7)
        self.assertEqual(len(body["results"]), 5)

    def test_publications_default_ordering_newest_first(self):
        results = self.client.get("/api/v1/publications/").json()["results"]
        self.assertEqual(results[0]["year"], 2024)  # the 2024 journal paper

    def test_publications_filter_by_author(self):
        resp = self.client.get(f"/api/v1/publications/?author={self.jon.url_name}")
        body = resp.json()
        self.assertEqual(body["count"], 6)
        titles = {r["title"] for r in body["results"]}
        self.assertNotIn("Unrelated Journal Paper", titles)

    def test_publications_filter_by_project(self):
        resp = self.client.get("/api/v1/publications/?project=projectsidewalk")
        self.assertEqual(resp.json()["count"], 6)

    def test_publications_filter_by_year(self):
        resp = self.client.get("/api/v1/publications/?year=2023")
        self.assertEqual(resp.json()["count"], 1)

    def test_publications_filter_by_type(self):
        self.assertEqual(
            self.client.get("/api/v1/publications/?type=Journal").json()["count"], 1
        )
        self.assertEqual(
            self.client.get("/api/v1/publications/?type=Conference").json()["count"], 6
        )

    def test_publication_detail_has_bibtex(self):
        pub = self.project_pubs[0]
        resp = self.client.get(f"/api/v1/publications/{pub.id}/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("bibtex", resp.json())

    def test_publication_urls_are_absolute(self):
        results = self.client.get("/api/v1/publications/").json()["results"]
        pub = results[0]
        self.assertTrue(pub["pdf_url"].startswith("http://"))
        # nested author page URL is absolute and points at /member/
        author_url = pub["authors"][0]["url"]
        self.assertTrue(author_url.startswith("http://"))
        self.assertIn("/member/", author_url)

    # ---- projects list + visibility gating ----------------------------------

    def test_projects_list_excludes_hidden(self):
        results = self.client.get("/api/v1/projects/").json()["results"]
        short_names = {p["short_name"] for p in results}
        self.assertIn("projectsidewalk", short_names)
        self.assertNotIn("secretproj", short_names)

    def test_hidden_project_detail_404(self):
        self.assertEqual(self.client.get("/api/v1/projects/secretproj/").status_code, 404)

    def test_unknown_project_detail_404(self):
        self.assertEqual(self.client.get("/api/v1/projects/nope/").status_code, 404)

    # ---- project sub-resources ----------------------------------------------

    def test_project_publications_subresource(self):
        resp = self.client.get("/api/v1/projects/projectsidewalk/publications/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["count"], 6)

    def test_project_grants_subresource(self):
        resp = self.client.get("/api/v1/projects/projectsidewalk/grants/")
        body = resp.json()
        self.assertEqual(body["count"], 1)
        grant = body["results"][0]
        self.assertEqual(grant["sponsor"]["short_name"], "NSF")
        # Funding amounts are intentionally not exposed by the public API.
        self.assertNotIn("funding_amount", grant)
        self._assert_no_internal_uw_fields(grant)

    # ---- grants: the internal/public boundary (#1448) ------------------------

    # UW's Workday codes are internal administrative data. GrantSerializer uses an
    # explicit field allowlist so they're excluded structurally — these tests keep
    # it that way if someone later switches to `exclude` or `fields = "__all__"`.
    INTERNAL_UW_FIELDS = ("uw_grant_id", "uw_award_number", "uw_award_name")

    def _assert_no_internal_uw_fields(self, grant):
        for field in self.INTERNAL_UW_FIELDS:
            self.assertNotIn(field, grant)

    def test_grants_list_omits_internal_uw_fields(self):
        resp = self.client.get("/api/v1/grants/")
        self.assertEqual(resp.status_code, 200)
        grant = resp.json()["results"][0]
        # The sponsor-side award ID stays public — it's the NSF number.
        self.assertEqual(grant["grant_id"], "1302338")
        self._assert_no_internal_uw_fields(grant)

    def test_grants_list_body_never_contains_a_worktag(self):
        """Belt-and-braces: the worktag must not leak through any nested
        serializer or added field either, so scan the whole response body."""
        body = self.client.get("/api/v1/grants/").content.decode()
        self.assertNotIn("GR012345", body)
        self.assertNotIn("AWD-00012345", body)
        self.assertNotIn("Internal UW Award Name", body)

    def test_project_people_subresource(self):
        resp = self.client.get("/api/v1/projects/projectsidewalk/people/")
        body = resp.json()
        # 3 roles: Jon's PI + Jon's past Co-PI + Past Lead's student-lead role.
        self.assertEqual(body["count"], 3)
        names = {r["person"]["name"] for r in body["results"]}
        self.assertEqual(names, {"Jon Froehlich", "Past Lead"})
        lead_roles = {r["lead_project_role"] for r in body["results"]}
        self.assertEqual(lead_roles, {"PI", "Co-PI", "Student Lead"})

    # ---- position held during a project role (#1426, #1435) -----------------
    #
    # These pin the *wire contract* -- that the resolved Position reaches the
    # payload, and at what cost. The resolution rules themselves (which Position
    # wins for overlapping / gapped / predating dates) are unit-tested directly
    # against the model in test_project_role.py, where a failure isolates.

    def _count_queries(self, url):
        # Warm the endpoint first: the *first* render generates each person's
        # cropped thumbnail (#1432), and easy-thumbnails writes a Source/
        # Thumbnail cache row per generated file. That cost is one-time -- the
        # cached path is filesystem stats only, no queries -- so measuring the
        # second call keeps this a test of the Position prefetch.
        self.assertEqual(self.client.get(url).status_code, 200)
        with CaptureQueriesContext(connection) as ctx:
            self.assertEqual(self.client.get(url).status_code, 200)
        return len(ctx)

    def _make_role_holder(self, first_name, positions, role_start,
                          role_end=None):
        """Create a person with the given ``(title, school, start, end)``
        positions and a single ProjectRole on self.project. Created per-test
        rather than in setUp so the fixture counts other tests assert stay put.
        """
        person = self.make_person(first_name=first_name, last_name="Holder")
        for title, school, start, end in positions:
            Position.objects.create(
                person=person, title=title, school=school,
                start_date=start, end_date=end,
            )
        ProjectRole.objects.create(
            person=person, project=self.project,
            start_date=role_start, end_date=role_end,
        )
        return person

    def _role_record(self, person):
        """Fetch the /people/ record for a person (they hold exactly one role)."""
        results = self.client.get(
            "/api/v1/projects/projectsidewalk/people/?page_size=100"
        ).json()["results"]
        matches = [r for r in results if r["person"]["id"] == person.id]
        self.assertEqual(len(matches), 1)
        return matches[0]

    def test_project_people_exposes_position_during_role(self):
        """A finished stint reports the latest position that overlapped it -- an
        undergrad who moved to an MS mid-stint reads 'MS Student', 'UW'."""
        person = self._make_role_holder(
            "Multi",
            positions=[
                (Title.UGRAD, "University of Maryland",
                 date(2015, 1, 1), date(2017, 5, 31)),
                (Title.MS_STUDENT, "University of Washington",
                 date(2017, 6, 1), date(2019, 6, 1)),
            ],
            role_start=date(2016, 1, 1),
            role_end=date(2018, 1, 1),
        )
        record = self._role_record(person)
        self.assertEqual(record["position_title"], "MS Student")
        self.assertEqual(record["position_school"], "University of Washington")
        self.assertEqual(record["position_school_abbreviated"], "UW")

    def test_project_people_active_role_reports_present_day_position(self):
        """#1435: a still-open role reports what the person is *today*, not what
        they were when the role began -- the case that had consumers fetching
        /people/<url_name>/ per roster row just to get a current title."""
        person = self._make_role_holder(
            "Promoted",
            positions=[
                (Title.ASSISTANT_PROF, "University of Maryland",
                 date(2012, 1, 1), date(2017, 8, 31)),
                (Title.FULL_PROF, "University of Washington",
                 date(2017, 9, 1), None),
            ],
            role_start=date(2012, 2, 1),
        )
        record = self._role_record(person)
        self.assertEqual(record["position_title"], "Professor")
        self.assertEqual(record["position_school"], "University of Washington")
        self.assertEqual(record["position_school_abbreviated"], "UW")

    def test_project_people_position_null_without_position(self):
        """self.past_lead has a project role but no Position at all."""
        record = self._role_record(self.past_lead)
        self.assertIsNone(record["position_title"])
        self.assertIsNone(record["position_school"])
        self.assertIsNone(record["position_school_abbreviated"])

    def test_project_people_does_not_scale_queries_with_rows(self):
        """N+1 guard: resolving each role's Position must ride on the view's
        prefetch, so query count is flat as the roster grows (#1426)."""
        url = "/api/v1/projects/projectsidewalk/people/?page_size=100"
        for i in range(3):
            self._make_role_holder(
                f"Small{i}",
                positions=[(Title.PHD_STUDENT, "University of Washington",
                            date(2015, 1, 1), None)],
                role_start=date(2016, 1, 1),
            )
        baseline = self._count_queries(url)

        for i in range(10):
            self._make_role_holder(
                f"Big{i}",
                positions=[(Title.PHD_STUDENT, "University of Washington",
                            date(2015, 1, 1), None)],
                role_start=date(2016, 1, 1),
            )
        self.assertEqual(self._count_queries(url), baseline)

    def test_project_leadership_subresource(self):
        resp = self.client.get("/api/v1/projects/projectsidewalk/leadership/")
        body = resp.json()
        pi_names = {r["person"]["name"] for r in body["pis"]}
        self.assertIn("Jon Froehlich", pi_names)

    def test_project_leadership_includes_all_time(self):
        """Leadership spans current AND past roles, including past roles held by
        someone who is currently active in another capacity."""
        body = self.client.get(
            "/api/v1/projects/projectsidewalk/leadership/"
        ).json()

        # Jon's past Co-PI role appears even though he's a current PI.
        copi = body["co_pis"]
        self.assertEqual(len(copi), 1)
        self.assertEqual(copi[0]["person"]["name"], "Jon Froehlich")
        self.assertFalse(copi[0]["is_active"])

        # A person whose only role was a past student lead still appears.
        leads = body["student_leads"]
        self.assertEqual({r["person"]["name"] for r in leads}, {"Past Lead"})
        self.assertFalse(leads[0]["is_active"])

    # ---- people -------------------------------------------------------------

    def test_people_list_scoped_to_members(self):
        results = self.client.get("/api/v1/people/").json()["results"]
        names = {p["name"] for p in results}
        self.assertIn("Jon Froehlich", names)  # has a Position
        self.assertNotIn("Ext Author", names)  # co-author only, no Position

    def test_person_detail_by_url_name(self):
        resp = self.client.get(f"/api/v1/people/{self.jon.url_name}/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["name"], "Jon Froehlich")

    def test_person_detail_exposes_current_school_and_department(self):
        """Affiliation for the team cards -- both come from the latest Position,
        like the already-exposed current_title (#1426)."""
        body = self.client.get(f"/api/v1/people/{self.jon.url_name}/").json()
        self.assertEqual(body["current_title"], "Professor")
        self.assertEqual(body["current_school"], "University of Washington")
        self.assertEqual(
            body["current_department"],
            "Allen School of Computer Science and Engineering",
        )

    def test_person_email_not_exposed(self):
        resp = self.client.get(f"/api/v1/people/{self.jon.url_name}/")
        self.assertNotIn("email", resp.json())

    # ---- CORS ---------------------------------------------------------------

    def test_cors_header_present_on_api(self):
        resp = self.client.get("/api/v1/publications/")
        self.assertEqual(resp["Access-Control-Allow-Origin"], "*")

    def test_cors_header_absent_off_api(self):
        resp = self.client.get("/version.json")
        self.assertNotIn("Access-Control-Allow-Origin", resp)

    def test_cors_options_preflight(self):
        resp = self.client.options("/api/v1/publications/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Access-Control-Allow-Origin"], "*")


# ---- image fields (#1432) ---------------------------------------------------


class ApiThumbnailTests(ApiTestCase):
    """``thumbnail`` is the cropped, sized derivative; ``image_original`` is the
    raw upload.

    Before #1432 the API handed out the raw file as ``thumbnail`` -- 33.5 MB for
    the 13 headshots Project Sidewalk's About page renders, framed however the
    original photo happened to be centered rather than by the editor's crop box.
    """

    CROP_BOX = "100,100,400,400"  # square, matching Person's crop ratio

    def _member_with_photo(self, cropping=CROP_BOX):
        """A lab member (Position -> visible in /people/) with a real photo."""
        person = self.make_person(
            first_name="Photo",
            last_name="Person",
            image=png_upload("photo_person.png"),
            cropping=cropping,
        )
        Position.objects.create(
            person=person, start_date=date(2020, 1, 1), title=Title.PHD_STUDENT
        )
        return person

    def _person_payload(self, person):
        resp = self.client.get(f"/api/v1/people/{person.url_name}/")
        self.assertEqual(resp.status_code, 200)
        return resp.json()

    def _media_path(self, url):
        """Filesystem path under MEDIA_ROOT for an absolute media URL."""
        path = unquote(urlparse(url).path)
        if path.startswith(settings.MEDIA_URL):
            path = path[len(settings.MEDIA_URL):]
        return os.path.join(settings.MEDIA_ROOT, path.lstrip("/"))

    def test_person_thumbnail_is_cropped_derivative(self):
        person = self._member_with_photo()
        body = self._person_payload(person)

        self.assertIn("256x256", body["thumbnail"])
        # The crop box reaches the derivative (commas are percent-encoded).
        self.assertIn("box-100%2C100%2C400%2C400", body["thumbnail"])
        self.assertTrue(body["thumbnail"].startswith("http://testserver"))
        self.assertNotEqual(body["thumbnail"], body["image_original"])

    def test_person_thumbnail_file_is_generated_at_the_requested_size(self):
        """Not just a URL: the file exists at 256x256, so a consumer that fetches
        it gets a real image rather than the 404s that made this unworkable."""
        body = self._person_payload(self._member_with_photo())
        with Image.open(self._media_path(body["thumbnail"])) as img:
            self.assertEqual(img.size, (256, 256))

    def test_person_image_original_is_the_raw_upload(self):
        person = self._member_with_photo()
        body = self._person_payload(person)
        self.assertIn(person.image.name, body["image_original"])
        self.assertTrue(body["image_original"].startswith("http://testserver"))

    def test_person_thumbnail_without_crop_box(self):
        """An editor who never touched the cropper still gets a sized thumbnail
        (ImageRatioField seeds a centered box on save; an empty one is a no-op)."""
        person = self._member_with_photo(cropping="")
        body = self._person_payload(person)
        self.assertIn("256x256", body["thumbnail"])

    def test_person_without_image_has_null_image_fields(self):
        person = self._member_with_photo()
        # .update() bypasses Person.save(), whose Star Wars fallback would
        # otherwise put an image back.
        Person.objects.filter(pk=person.pk).update(image="", cropping="")
        body = self._person_payload(person)
        self.assertIsNone(body["thumbnail"])
        self.assertIsNone(body["image_original"])

    def test_project_people_nested_person_carries_cropped_thumbnail(self):
        """The roster reads the nested person, so the cropped URL has to be there
        too -- otherwise it's a second request per member just for a photo."""
        person = self._member_with_photo()
        ProjectRole.objects.create(
            person=person, project=self.project, start_date=date(2020, 1, 1)
        )
        results = self.client.get(
            "/api/v1/projects/projectsidewalk/people/?page_size=100"
        ).json()["results"]
        record = next(r for r in results if r["person"]["id"] == person.id)

        self.assertIn("256x256", record["person"]["thumbnail"])
        self.assertIn(person.image.name, record["person"]["image_original"])

    def test_project_thumbnail_is_cropped_derivative(self):
        project = self.make_project(
            name="Cropped Project",
            short_name="croppedproj",
            is_visible=True,
            gallery_image=png_upload("cropped_proj.png", size=(1600, 1200)),
            cropping="0,100,1500,1000",  # 15:9, matching Project's crop ratio
        )
        body = self.client.get("/api/v1/projects/croppedproj/").json()

        self.assertIn("1000x600", body["thumbnail"])
        self.assertIn("box-0%2C100%2C1500%2C1000", body["thumbnail"])
        self.assertIn(project.gallery_image.name, body["image_original"])
        with Image.open(self._media_path(body["thumbnail"])) as img:
            self.assertEqual(img.size, (1000, 600))

    def test_thumbnail_falls_back_to_original_when_source_is_missing(self):
        """A row whose file vanished must not 500 the whole list response."""
        person = self._member_with_photo()
        default_storage.delete(person.image.name)

        with self.assertLogs("website.utils.thumbnail_utils", level="WARNING"):
            body = self._person_payload(person)

        self.assertEqual(body["thumbnail"], body["image_original"])

    def test_helper_returns_none_when_source_is_missing(self):
        person = self._member_with_photo()
        default_storage.delete(person.image.name)

        with self.assertLogs("website.utils.thumbnail_utils", level="WARNING"):
            thumbnail = get_cropped_thumbnail(
                person.image, API_PERSON_THUMBNAIL_SIZE, person.cropping
            )
        self.assertIsNone(thumbnail)


class ApiThumbnailAspectTests(SimpleTestCase):
    """Guard against re-introducing the double-crop that clipped heads off the
    news cards (#1424): crop_corners applies the editor's box, then scale_and_crop
    center-crops again if the requested size's aspect ratio disagrees."""

    def test_api_sizes_match_the_models_crop_ratios(self):
        for label, api_size, model_size in (
            ("person", API_PERSON_THUMBNAIL_SIZE, PERSON_THUMBNAIL_SIZE),
            ("project", API_PROJECT_THUMBNAIL_SIZE, PROJECT_THUMBNAIL_SIZE),
        ):
            with self.subTest(label):
                self.assertAlmostEqual(
                    api_size[0] / api_size[1],
                    model_size[0] / model_size[1],
                    places=3,
                    msg=f"API {label} size {api_size} must keep the aspect ratio "
                        f"of the model's crop box {model_size}",
                )
