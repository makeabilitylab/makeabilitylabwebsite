"""
Regression tests for the Award model's Awards-page display logic (#1294 follow-up:
Awards redesign).

These pin Award.get_anchor_kind() — which picks the left-side visual the Awards
page shows per award (recipient portrait / project thumbnail / medal icon /
uploaded badge) — and the helpers it relies on, plus a smoke test that the
public Awards page renders the new card markup. The branching is easy to break
when award types or visibility rules change, and it's only reachable through a
real queryset (M2M relations, project visibility), so it belongs here rather
than in a SimpleTestCase.
"""

from datetime import date

from django.urls import reverse

from website.models.award import Award, AwardType
from website.tests.base import DatabaseTestCase
from website.tests.factories import image_upload


class AwardAnchorTests(DatabaseTestCase):
    """Award.get_anchor_kind() and its supporting helpers."""

    def make_award(self, award_type, recipients=(), projects=(), **kwargs):
        kwargs.setdefault("title", "Test Award")
        kwargs.setdefault("date", date(2020, 1, 1))
        award = Award.objects.create(award_type=award_type, **kwargs)
        if recipients:
            award.recipients.set(recipients)
        if projects:
            award.projects.set(projects)
        return award

    def test_faculty_honor_uses_medal(self):
        person = self.make_person()
        award = self.make_award(AwardType.FACULTY_HONOR, recipients=[person])
        self.assertEqual(award.get_anchor_kind(), "medal")

    def test_student_award_uses_recipient_portrait(self):
        person = self.make_person()  # factory pre-sets an image
        award = self.make_award(AwardType.STUDENT_AWARD, recipients=[person])
        self.assertEqual(award.get_anchor_kind(), "portrait")
        self.assertEqual(award.get_portrait_person(), person)

    def test_phd_fellowship_uses_portrait(self):
        person = self.make_person()
        award = self.make_award(AwardType.PHD_FELLOWSHIP, recipients=[person])
        self.assertEqual(award.get_anchor_kind(), "portrait")

    def test_student_award_without_a_photo_recipient_falls_back_to_medal(self):
        # A student-typed award honoring only a project (no person) has no
        # portrait to show, so it must fall back to the medal icon.
        project = self.make_project(is_visible=True, with_thumbnail=True)
        award = self.make_award(AwardType.STUDENT_AWARD, projects=[project])
        self.assertIsNone(award.get_portrait_person())
        self.assertEqual(award.get_anchor_kind(), "medal")

    def test_project_award_uses_thumbnail(self):
        project = self.make_project(is_visible=True, with_thumbnail=True)
        award = self.make_award(AwardType.PROJECT_AWARD, projects=[project])
        self.assertEqual(award.get_anchor_kind(), "thumbnail")
        self.assertEqual(award.get_thumbnail_project(), project)

    def test_project_award_without_thumbnail_falls_back_to_medal(self):
        project = self.make_project(is_visible=True)  # no gallery_image
        award = self.make_award(AwardType.PROJECT_AWARD, projects=[project])
        self.assertIsNone(award.get_thumbnail_project())
        self.assertEqual(award.get_anchor_kind(), "medal")

    def test_project_award_ignores_private_project_for_thumbnail(self):
        # #1300: private projects must not surface on the public Awards page.
        project = self.make_project(is_visible=False, with_thumbnail=True)
        award = self.make_award(AwardType.PROJECT_AWARD, projects=[project])
        self.assertIsNone(award.get_thumbnail_project())
        self.assertEqual(award.get_anchor_kind(), "medal")

    def test_badge_overrides_category_anchor(self):
        # An uploaded badge wins even for a student award with a photographed
        # recipient.
        person = self.make_person()
        award = self.make_award(
            AwardType.STUDENT_AWARD,
            recipients=[person],
            badge=image_upload("badge.gif"),
        )
        self.assertEqual(award.get_anchor_kind(), "badge")

    def test_badge_alt_text_defaults_to_title(self):
        award = self.make_award(
            AwardType.FACULTY_HONOR,
            title="NSF CAREER Award",
            recipients=[self.make_person()],
        )
        self.assertEqual(award.get_badge_alt_text(), "NSF CAREER Award")
        award.badge_alt_text = "NSF logo"
        self.assertEqual(award.get_badge_alt_text(), "NSF logo")


class AwardsPageRenderTests(DatabaseTestCase):
    """The public Awards page renders the redesigned card markup."""

    def test_awards_page_renders_card_with_year_and_anchor_kind(self):
        person = self.make_person(first_name="Ada", last_name="Lovelace")
        Award.objects.create(
            title="A Faculty Honor",
            date=date(2017, 5, 1),
            award_type=AwardType.FACULTY_HONOR,
        ).recipients.set([person])

        response = self.client.get(reverse("website:awards"))
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertIn("award-card", html)
        self.assertIn("award-card--medal", html)  # faculty honor -> medal anchor
        self.assertIn("2017", html)                # prominent year is rendered
