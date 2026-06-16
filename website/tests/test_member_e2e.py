"""
End-to-end browser smoke tests for the member page's interactive bits (#1110):
the "Load more" / "Load all" controls, the no-overflow hidden state, the
live loaded/total section counts, the section nav, and the bio toggle.

These exercise the JavaScript (member-load-more.js, bio-expand.js) that the
Django test client can't run. They use Playwright against a live server.

WHY SKIP-GUARDED: Playwright and its browser aren't part of the normal test
image, so this module SKIPS itself (rather than erroring) when either is
missing. `python manage.py test website` stays green without them.

To run locally / in CI:
    pip install playwright
    python -m playwright install --with-deps chromium
    python manage.py test website.tests.test_member_e2e \
        --settings=makeabilitylab.settings_test

Notes:
  - StaticLiveServerTestCase serves collected/​app static files, so the JS/CSS
    under test are actually loaded by the browser.
  - It subclasses TransactionTestCase, so fixtures are created in setUp and are
    visible to the live-server thread (unlike TestCase's per-test transaction).
"""

import os
import unittest

from django.contrib.staticfiles.testing import StaticLiveServerTestCase

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
    _PLAYWRIGHT_IMPORT_ERROR = None
except Exception as exc:  # pragma: no cover - environment dependent
    sync_playwright = None
    PWTimeout = Exception
    _PLAYWRIGHT_IMPORT_ERROR = exc

# Playwright's sync API spins up its own subprocess; allow it inside Django's
# test thread.
os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "1")

_LONG_BIO = (
    "<p>" + ("This is a deliberately long bio sentence that wraps several "
             "times so it exceeds the three-line collapse threshold. ") * 12
    + "</p>"
)


@unittest.skipIf(sync_playwright is None,
                 f"Playwright not installed ({_PLAYWRIGHT_IMPORT_ERROR})")
class MemberPageE2ETests(StaticLiveServerTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        try:
            cls._pw = sync_playwright().start()
            cls._browser = cls._pw.chromium.launch()
        except Exception as exc:  # browser binary missing, etc.
            super().tearDownClass()
            raise unittest.SkipTest(f"Chromium unavailable for Playwright: {exc}")

    @classmethod
    def tearDownClass(cls):
        try:
            cls._browser.close()
            cls._pw.stop()
        finally:
            super().tearDownClass()

    # ---- fixtures -----------------------------------------------------------

    def _make_person(self, **kwargs):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from website.models import Person
        gif = (b"GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00"
               b"!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01"
               b"\x00\x00\x02\x02D\x01\x00;")
        kwargs.setdefault("first_name", "E2E")
        kwargs.setdefault("last_name", "Tester")
        kwargs.setdefault("image", SimpleUploadedFile("a.gif", gif, content_type="image/gif"))
        kwargs.setdefault("easter_egg", SimpleUploadedFile("b.gif", gif, content_type="image/gif"))
        return Person.objects.create(**kwargs)

    def _make_talks(self, person, n):
        from datetime import date
        from django.core.files.uploadedfile import SimpleUploadedFile
        from website.models import Talk
        from website.models.talk import TalkType
        for i in range(n):
            talk = Talk.objects.create(
                title=f"Talk number {i}",
                date=date(2024, 1, 1),
                forum_name="CHI",
                talk_type=TalkType.CONFERENCE_TALK,
                pdf_file=SimpleUploadedFile(f"t{i}.pdf", b"%PDF-1.4 test",
                                            content_type="application/pdf"),
            )
            talk.authors.add(person)

    def _make_papers(self, person, n):
        from datetime import date
        from django.core.files.uploadedfile import SimpleUploadedFile
        from website.models import Publication
        from website.models.publication import PubType
        for i in range(n):
            pub = Publication.objects.create(
                title=f"Paper number {i}", date=date(2024, 1, 1), forum_name="CHI",
                pub_venue_type=PubType.CONFERENCE,
                pdf_file=SimpleUploadedFile(f"p{i}.pdf", b"%PDF-1.4 test",
                                            content_type="application/pdf"),
            )
            pub.authors.add(person)

    def _make_projects(self, person, n):
        from datetime import date
        from website.models import Project, ProjectRole
        for i in range(n):
            letter = chr(ord("A") + i)
            proj = Project.objects.create(
                name=f"Project {letter}", short_name=f"project{letter.lower()}",
                is_visible=True,
            )
            ProjectRole.objects.create(person=person, project=proj,
                                       start_date=date(2024, 1, 1))

    def _goto(self, person):
        page = self._browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto(f"{self.live_server_url}/member/{person.url_name}/")
        return page

    # ---- tests --------------------------------------------------------------

    def _talk_card_count(self, page):
        return page.locator("#person-talks-grid .talk-card").count()

    def test_load_more_appends_until_complete(self):
        person = self._make_person()
        self._make_talks(person, 20)  # > talks page size (8)
        page = self._goto(person)
        try:
            page.wait_for_selector("#person-talks-grid .talk-card")
            self.assertEqual(self._talk_card_count(page), 8)
            # Heading carries a live loaded/total count (no "Recent" wording).
            self.assertIn("(8/20)", page.inner_text("#talks-heading"))

            more = page.locator('[data-artifact-type="talks"] [data-load-more]')
            self.assertRegex(more.inner_text(), r"Load \d+ more talks")

            more.click()  # 8 -> 16
            page.wait_for_function(
                "document.querySelectorAll('#person-talks-grid .talk-card').length === 16"
            )

            more.click()  # 16 -> 20 (last batch)
            page.wait_for_function(
                "document.querySelectorAll('#person-talks-grid .talk-card').length === 20"
            )
            # Everything shown: controls removed and the heading count is full.
            self.assertEqual(
                page.locator('[data-artifact-type="talks"]').count(), 0)
            self.assertIn("(20/20)", page.inner_text("#talks-heading"))
        finally:
            page.close()

    def test_load_all_loads_everything_and_updates_count(self):
        person = self._make_person()
        self._make_talks(person, 20)
        page = self._goto(person)
        try:
            page.wait_for_selector("#person-talks-grid .talk-card")
            self.assertEqual(self._talk_card_count(page), 8)

            all_btn = page.locator('[data-artifact-type="talks"] [data-load-all]')
            self.assertRegex(all_btn.inner_text(), r"Load all \d+ talks")
            all_btn.click()
            page.wait_for_function(
                "document.querySelectorAll('#person-talks-grid .talk-card').length === 20"
            )
            self.assertEqual(
                page.locator('[data-artifact-type="talks"]').count(), 0)
            # The heading's loaded/total count reaches full.
            self.assertIn("(20/20)", page.inner_text("#talks-heading"))
        finally:
            page.close()

    def test_projects_controls_hidden_when_no_overflow(self):
        # Exactly page-size (8) projects -> nothing more to load -> the projects
        # controls must NOT be visible on desktop. This is the regression guard
        # for the display:flex-overriding-[hidden] bug (#1110).
        person = self._make_person()
        self._make_projects(person, 8)
        page = self._goto(person)
        try:
            page.wait_for_selector("#person-projects-grid .project-card")
            controls = page.locator('[data-artifact-type="projects"]')
            self.assertEqual(controls.count(), 1)
            self.assertFalse(controls.is_visible())
        finally:
            page.close()

    def test_section_nav_highlights_and_jumps(self):
        person = self._make_person()
        self._make_papers(person, 7)   # -> Papers section
        self._make_talks(person, 9)    # -> Talks section
        page = self._goto(person)
        try:
            nav = page.locator("[data-member-section-nav]")
            page.wait_for_selector("[data-member-section-nav]")
            self.assertEqual(nav.locator("a").count(), 2)  # Papers + Talks
            nav.locator('[data-section-link="person-talks"]').click()
            page.wait_for_function(
                "document.querySelector('[data-section-link=\"person-talks\"]')"
                ".getAttribute('aria-current') === 'location'"
            )
        finally:
            page.close()

    def test_nav_name_reveals_on_scroll(self):
        person = self._make_person(first_name="Ada", last_name="Lovelace")
        self._make_talks(person, 20)  # long enough to scroll the <h1> away
        page = self._goto(person)
        try:
            name = page.locator("[data-nav-name]")
            page.wait_for_selector("[data-member-section-nav]")
            self.assertFalse(name.is_visible())  # hidden while the <h1> shows
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            name.wait_for(state="visible")
            self.assertIn("Ada Lovelace", name.inner_text())
        finally:
            page.close()

    def test_nav_count_updates_on_load_more(self):
        person = self._make_person()
        self._make_talks(person, 20)
        page = self._goto(person)
        try:
            count = page.locator(
                '[data-section-link="person-talks"] .member-section-nav-count')
            page.wait_for_selector("[data-member-section-nav]")
            self.assertEqual(count.inner_text(), "(8/20)")
            page.locator('[data-artifact-type="talks"] [data-load-more]').click()
            page.wait_for_function(
                "document.querySelector('[data-section-link=\"person-talks\"] "
                ".member-section-nav-count').textContent === '(16/20)'"
            )
        finally:
            page.close()

    def test_back_to_top_appears_and_scrolls(self):
        person = self._make_person()
        self._make_talks(person, 20)  # long page
        page = self._goto(person)
        try:
            btn = page.locator(".back-to-top")
            self.assertFalse(btn.is_visible())  # hidden at the top
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            btn.wait_for(state="visible")
            btn.click()
            page.wait_for_function("window.scrollY === 0")
        finally:
            page.close()

    def test_bio_show_more_then_less_stays_collapsed(self):
        person = self._make_person(bio=_LONG_BIO)
        page = self._goto(person)
        try:
            toggle = page.locator(".bio-toggle")
            page.wait_for_selector(".bio-toggle")
            self.assertEqual(toggle.get_attribute("aria-expanded"), "false")
            toggle.click()
            self.assertEqual(toggle.get_attribute("aria-expanded"), "true")
            toggle.click()
            # The reported bug: it bounced back open. It must stay collapsed.
            self.assertEqual(toggle.get_attribute("aria-expanded"), "false")
        finally:
            page.close()
