"""
Tests for UW grant tracking (#1448).

Two features, one shared privacy boundary:

1. ``Grant.uw_grant_id`` / ``uw_award_number`` / ``uw_award_name`` — UW's internal
   Workday codes. Sponsored-programs staff ask for the worktag constantly, so PhD
   students (the ``Editors`` group) can now *view* grants to look one up. They must
   NOT see the funding data or proposal files that were the reason Grant was
   superuser-only in the first place (#1125).

2. ``GrantTrackingLink`` — superuser-only bookmarks to the official UW CSE and UW
   Award Portal trackers, rendered atop the Grant changelist. These live in the DB
   rather than in source because the real URLs embed per-PI SharePoint sharing
   tokens and this repository is public.

The API-side half of the boundary (the ``uw_*`` fields must never be serialized)
is pinned in ``test_api.py``.
"""

from datetime import date

from django.contrib.auth.models import Group, User
from django.core.management import call_command

from website.models import Grant, GrantTrackingLink, Sponsor
from website.tests.base import DatabaseTestCase

CHANGELIST_URL = "/admin/website/grant/"
TRACKING_LINK_URL = "/admin/website/granttrackinglink/"

# A stand-in for the real UW CSE SharePoint link: those carry a pile of query
# parameters and run well past Django's 200-char URLField default. Built here
# rather than hard-coded so no real sharing token lands in the repo.
LONG_SHAREPOINT_URL = (
    "https://example.sharepoint.com/sites/cse_research_administration/"
    "Shared%20Documents/Forms/AllItems.aspx?"
    + "&".join(f"param{i}=value{i}value{i}" for i in range(20))
)


class GrantUwFieldTests(DatabaseTestCase):
    """The three UW fields are optional and round-trip unchanged."""

    def setUp(self):
        self.sponsor = Sponsor.objects.create(name="National Science Foundation",
                                              short_name="NSF")

    def test_uw_fields_are_optional(self):
        """Every existing grant predates these fields, so blank must be legal —
        both in the database (null) and in the admin form (blank)."""
        grant = Grant.objects.create(title="No UW codes yet", sponsor=self.sponsor,
                                     date=date(2015, 1, 1))
        grant.refresh_from_db()
        self.assertIsNone(grant.uw_grant_id)
        self.assertIsNone(grant.uw_award_number)
        self.assertIsNone(grant.uw_award_name)

        for name in ("uw_grant_id", "uw_award_number", "uw_award_name"):
            field = Grant._meta.get_field(name)
            self.assertTrue(field.null, f"{name} must be null=True")
            self.assertTrue(field.blank, f"{name} must be blank=True")

    def test_uw_fields_round_trip(self):
        grant = Grant.objects.create(
            title="Funded thing", sponsor=self.sponsor, date=date(2020, 1, 1),
            uw_grant_id="GR012345, GR012346",  # one award can span several worktags
            uw_award_number="AWD-00012345",
            uw_award_name="Accessible Sidewalks: A Really Long UW Award Name",
        )
        grant.refresh_from_db()
        self.assertEqual(grant.uw_grant_id, "GR012345, GR012346")
        self.assertEqual(grant.uw_award_number, "AWD-00012345")
        self.assertEqual(grant.uw_award_name,
                         "Accessible Sidewalks: A Really Long UW Award Name")

    def test_sponsor_grant_id_is_untouched(self):
        """``grant_id`` still means the *sponsor's* award ID (NSF-style) and is
        public. The UW worktag is a separate, internal field — regression guard
        against anyone collapsing the two."""
        grant = Grant.objects.create(title="Both IDs", sponsor=self.sponsor,
                                     date=date(2020, 1, 1),
                                     grant_id="1302338", uw_grant_id="GR012345")
        grant.refresh_from_db()
        self.assertEqual(grant.grant_id, "1302338")
        self.assertEqual(grant.uw_grant_id, "GR012345")


class GrantTrackingLinkModelTests(DatabaseTestCase):

    def test_long_sharepoint_url_round_trips(self):
        """Pins ``max_length=1000`` on the URLField. Django's 200-char default
        would reject the real UW CSE SharePoint link outright (Postgres raises on
        save; full_clean raises before that)."""
        self.assertGreater(len(LONG_SHAREPOINT_URL), 200)
        link = GrantTrackingLink(label="UW CSE Financial Reporting",
                                 url=LONG_SHAREPOINT_URL)
        link.full_clean()
        link.save()
        link.refresh_from_db()
        self.assertEqual(link.url, LONG_SHAREPOINT_URL)

    def test_default_ordering_is_display_order_then_label(self):
        GrantTrackingLink.objects.create(label="Zebra", url="https://z.example.com",
                                         display_order=1)
        GrantTrackingLink.objects.create(label="Apple", url="https://a.example.com",
                                         display_order=1)
        GrantTrackingLink.objects.create(label="First", url="https://f.example.com",
                                         display_order=0)
        self.assertEqual([l.label for l in GrantTrackingLink.objects.all()],
                         ["First", "Apple", "Zebra"])

    def test_str_is_the_label(self):
        link = GrantTrackingLink.objects.create(label="UW Award Portal",
                                                url="https://example.com")
        self.assertEqual(str(link), "UW Award Portal")


class GrantAdminAccessTests(DatabaseTestCase):
    """Who sees what on the Grant admin pages.

    The rule: Editors may *look up a worktag*; everything that made Grant
    superuser-only (funding amounts, proposal PDFs, the total-funding rollup, the
    tracking-link bookmarks) stays with the superuser.
    """

    def setUp(self):
        call_command("setup_admin_groups")

        self.sponsor = Sponsor.objects.create(name="National Science Foundation",
                                              short_name="NSF")
        self.grant = Grant.objects.create(
            title="NSF Award for Sidewalk", sponsor=self.sponsor,
            date=date(2015, 1, 1), funding_amount=1234567,
            grant_id="1302338", uw_grant_id="GR012345",
            uw_award_number="AWD-00012345", uw_award_name="Sidewalk Award",
        )
        GrantTrackingLink.objects.create(label="UW CSE Financial Reporting",
                                         url=LONG_SHAREPOINT_URL, display_order=0)
        GrantTrackingLink.objects.create(label="UW Award Portal",
                                         url="https://example.finance.uw.edu/fin/AwardPortal",
                                         display_order=1)

        self.superuser = User.objects.create_superuser("boss", "boss@example.com", "x")
        self.editor = User.objects.create_user("ed", is_staff=True)
        self.editor.groups.add(Group.objects.get(name="Editors"))
        self.contributor = User.objects.create_user("intern", is_staff=True)
        self.contributor.groups.add(Group.objects.get(name="Contributors"))

    # ---- superuser ----------------------------------------------------------

    def test_superuser_sees_tracking_links_and_funding(self):
        self.client.force_login(self.superuser)
        content = self.client.get(CHANGELIST_URL).content.decode()
        self.assertIn("UW CSE Financial Reporting", content)
        self.assertIn("UW Award Portal", content)
        self.assertIn("Total Funding", content)
        self.assertIn("1,234,567", content)
        self.assertIn("GR012345", content)

    def test_tracking_links_render_in_display_order(self):
        self.client.force_login(self.superuser)
        content = self.client.get(CHANGELIST_URL).content.decode()
        self.assertLess(content.index("UW CSE Financial Reporting"),
                        content.index("UW Award Portal"))

    def test_superuser_change_form_has_all_fields(self):
        self.client.force_login(self.superuser)
        content = self.client.get(f"{CHANGELIST_URL}{self.grant.pk}/change/").content.decode()
        self.assertIn('name="funding_amount"', content)
        self.assertIn('name="pdf_file"', content)
        self.assertIn('name="uw_grant_id"', content)

    # ---- Editors (PhD students): read-only worktag lookup --------------------

    def test_editor_can_view_changelist_and_see_worktag(self):
        self.client.force_login(self.editor)
        resp = self.client.get(CHANGELIST_URL)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("GR012345", resp.content.decode())

    def test_editor_does_not_see_tracking_links_or_funding_totals(self):
        self.client.force_login(self.editor)
        content = self.client.get(CHANGELIST_URL).content.decode()
        self.assertNotIn("UW CSE Financial Reporting", content)
        self.assertNotIn("UW Award Portal", content)
        self.assertNotIn("Total Funding", content)
        self.assertNotIn("1,234,567", content)

    def test_editor_change_form_hides_funding_and_files_and_is_readonly(self):
        self.client.force_login(self.editor)
        content = self.client.get(
            f"{CHANGELIST_URL}{self.grant.pk}/change/").content.decode()
        self.assertIn("GR012345", content)          # the whole point
        self.assertIn("AWD-00012345", content)
        self.assertNotIn("funding_amount", content)
        self.assertNotIn("pdf_file", content)
        self.assertNotIn("raw_file", content)
        self.assertNotIn("1234567", content)
        # View-only permission => Django renders no save buttons at all.
        self.assertNotIn('name="_save"', content)

    def test_editor_readonly_form_labels_disambiguate_the_two_grant_ids(self):
        """The read-only form Editors see must still distinguish the sponsor's
        award ID from UW's worktag.

        Django's readonly rendering resolves labels through
        ``admin.utils.label_for_field``, which reads the *model's* verbose_name
        and ignores any label set on the ModelAdmin form — so these labels only
        work because they're declared on the model fields. Regression guard for
        anyone who moves them back into GrantAdmin.get_form.
        """
        self.client.force_login(self.editor)
        content = self.client.get(
            f"{CHANGELIST_URL}{self.grant.pk}/change/").content.decode()
        self.assertIn("Sponsor grant ID", content)
        self.assertIn("UW Grant ID (worktag)", content)

    def test_editor_cannot_add_or_delete_grants(self):
        self.client.force_login(self.editor)
        self.assertEqual(self.client.get(f"{CHANGELIST_URL}add/").status_code, 403)
        self.assertEqual(
            self.client.get(f"{CHANGELIST_URL}{self.grant.pk}/delete/").status_code, 403)

    def test_editor_cannot_reach_the_tracking_links_themselves(self):
        """The bookmarks are the superuser's own financial-reporting links."""
        self.client.force_login(self.editor)
        self.assertEqual(self.client.get(TRACKING_LINK_URL).status_code, 403)

    # ---- Contributors (ugrads): no grant access at all -----------------------

    def test_contributor_cannot_view_grants(self):
        self.client.force_login(self.contributor)
        self.assertEqual(self.client.get(CHANGELIST_URL).status_code, 403)
        self.assertEqual(self.client.get(TRACKING_LINK_URL).status_code, 403)
