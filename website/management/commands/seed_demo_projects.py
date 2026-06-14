"""
Local-dev helper: seed three demo projects designed to exercise the project
page sidebar in its three interesting states.

Run inside the website container:

    python manage.py seed_demo_projects

Idempotent — on each run it deletes any prior demo data (anything whose
short_name starts with `demo-` or whose owner is a Person with
first_name="Demo") and recreates from scratch, so it's safe to re-run after
edits to the seed data.

Demo projects:

The four projects cover a 2x2 matrix of main-content-height x sidebar-
content-height, so the project-page layout can be eyeballed in each
combination:

                       SHORT sidebar       TALL sidebar
                       --------------      -----------------------------
SHORT main content     demo-active-small   (n/a — covered by tall main)
TALL main content      demo-tall-main-     demo-active-tall (active)
                       short-sidebar       demo-ended-tall  (ended)

- /project/demo-active-small/             Short main, short sidebar.
                                          1 PI + 1 Student Lead, no
                                          publications. Baseline.

- /project/demo-active-tall/              Tall main + tall sidebar
                                          (Sidewalk-like, active project).
                                          3 active PIs/Co-PIs + 3 active
                                          Student Leads + 5 alumni + ~15
                                          publications. "Former" prefix
                                          should still show on the inactive
                                          headers because the project
                                          itself is still active.

- /project/demo-ended-tall/               Tall main + tall sidebar (ENDED).
                                          Same role structure but all roles
                                          ended before project.end_date.
                                          Use to confirm the "Former"
                                          prefix is dropped (#1245) when
                                          the project itself has ended.

- /project/demo-tall-main-short-sidebar/  Tall main + short sidebar. Tests
                                          the post-sidebar "lopsided"
                                          regions when the sidebar bottom
                                          is reached well before the main
                                          content ends, and confirms
                                          sticky keeps a short sidebar in
                                          view while reading a long page.

NOTE: sponsors/grants intentionally omitted — the sidebar's Funding
section pulls from Sponsor via Grant.sponsor → Grant.projects M2M, which
would require wiring up a small Artifact/Grant chain. Out of scope for
this seed; the lead-role sections are enough to exercise both #1245 fixes.

This file lives in management/commands/ so Django auto-discovers it, but it's
explicitly a dev/test tool — don't wire it into docker-entrypoint.sh.
"""

from datetime import date, timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management.base import BaseCommand


# Minimal 1x1 GIF used to satisfy Person.image / Person.easter_egg without
# triggering Person.save()'s Star Wars fallback (which opens a real file).
_GIF_1PX = (
    b"GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00"
    b"!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01"
    b"\x00\x00\x02\x02D\x01\x00;"
)


def _img(name):
    return SimpleUploadedFile(name, _GIF_1PX, content_type="image/gif")


class Command(BaseCommand):
    help = "Seed three demo projects (see file docstring) for visual testing of project page layouts."

    def handle(self, *args, **opts):
        from website.models import Grant, Person, Project, Publication, Sponsor
        from website.models.project_role import LeadProjectRoleTypes, ProjectRole

        self._wipe_prior(Person, Project, Publication, Grant, Sponsor)
        self.stdout.write(self.style.NOTICE("Creating demo people, sponsors, projects, and publications…"))

        people = self._make_demo_people(Person)
        sponsors = self._make_demo_sponsors(Sponsor)

        small = self._make_demo_active_small(Project, ProjectRole, LeadProjectRoleTypes, people)
        active_tall = self._make_demo_active_tall(Project, ProjectRole, LeadProjectRoleTypes, people)
        ended_tall = self._make_demo_ended_tall(Project, ProjectRole, LeadProjectRoleTypes, people)
        tall_main = self._make_demo_tall_main_short_sidebar(Project, ProjectRole, LeadProjectRoleTypes, people)

        # Sponsor coverage: small gets 1 sponsor; the others get the full 4 to
        # exercise multi-logo wrapping and verify the funding row layout.
        self._attach_grant(Grant, small, sponsors[:1], year=2024)
        self._attach_grant(Grant, active_tall, sponsors, year=2019)
        self._attach_grant(Grant, ended_tall, sponsors[:3], year=2018)
        self._attach_grant(Grant, tall_main, sponsors[:2], year=2024)

        self._make_demo_publications(Publication, active_tall, people, count=15, start_year=2019, end_year=2025)
        self._make_demo_publications(Publication, ended_tall, people, count=15, start_year=2018, end_year=2022)
        self._make_demo_publications(Publication, tall_main, people, count=15, start_year=2024, end_year=2025)

        self.stdout.write(self.style.SUCCESS("\nDone. Visit:"))
        for slug in (
            "demo-active-small",
            "demo-active-tall",
            "demo-ended-tall",
            "demo-tall-main-short-sidebar",
        ):
            self.stdout.write(f"  http://localhost:8571/project/{slug}/")

    # ------------------------------------------------------------------
    # Cleanup

    def _wipe_prior(self, Person, Project, Publication, Grant, Sponsor):
        """Delete any prior demo data so the command is safe to re-run."""
        n_projects = Project.objects.filter(short_name__startswith="demo-").count()
        n_people = Person.objects.filter(first_name="Demo").count()
        n_pubs = Publication.objects.filter(title__startswith="Demo Paper:").count()
        n_grants = Grant.objects.filter(title__startswith="Demo Grant:").count()
        n_sponsors = Sponsor.objects.filter(name__startswith="Demo ").count()
        if n_projects or n_people or n_pubs or n_grants or n_sponsors:
            self.stdout.write(self.style.WARNING(
                f"Removing prior demo data: {n_projects} projects, {n_people} people, "
                f"{n_pubs} publications, {n_grants} grants, {n_sponsors} sponsors."
            ))
            Publication.objects.filter(title__startswith="Demo Paper:").delete()
            Grant.objects.filter(title__startswith="Demo Grant:").delete()
            Project.objects.filter(short_name__startswith="demo-").delete()
            Sponsor.objects.filter(name__startswith="Demo ").delete()
            Person.objects.filter(first_name="Demo").delete()

    # ------------------------------------------------------------------
    # Fixture creation

    # Names cycle through so each project gets distinct-looking faculty + students
    # in the sidebar. Using "Demo" as first_name makes cleanup trivial.
    _PEOPLE = [
        # (last_name, role label — purely for self-documentation)
        ("Lovelace", "faculty"),
        ("Turing", "faculty"),
        ("Hopper", "faculty"),
        ("Knuth", "faculty"),
        ("Wing", "faculty"),
        ("Liskov", "faculty"),
        ("Allen", "student"),
        ("Babbage", "student"),
        ("Curie", "student"),
        ("Darwin", "student"),
        ("Einstein", "student"),
        ("Feynman", "student"),
        ("Goldberg", "student"),
        ("Hamilton", "student"),
        ("Iverson", "student"),
        ("Joliot", "student"),
        ("Kepler", "student"),
        ("Lamarr", "student"),
    ]

    def _make_demo_people(self, Person):
        """Create one Person per (Demo, LastName) pair and return dict by last name."""
        people = {}
        for last_name, _role in self._PEOPLE:
            p = Person.objects.create(
                first_name="Demo",
                last_name=last_name,
                image=_img(f"demo_{last_name.lower()}.gif"),
                easter_egg=_img(f"demo_{last_name.lower()}_egg.gif"),
            )
            people[last_name] = p
        return people

    # --- Sponsors / Grants -------------------------------------------------

    _SPONSORS = [
        ("Demo Science Foundation", "DSF", "https://example.org/dsf"),
        ("Demo Research Council", "DRC", "https://example.org/drc"),
        ("Demo Tech Institute", "DTI", "https://example.org/dti"),
        ("Demo Industry Partner", "DIP", "https://example.org/dip"),
    ]

    def _make_demo_sponsors(self, Sponsor):
        sponsors = []
        for name, short_name, url in self._SPONSORS:
            s = Sponsor.objects.create(
                name=name,
                short_name=short_name,
                url=url,
                alt_text=f"{name} logo",
                icon=_img(f"{short_name.lower()}_icon.gif"),
            )
            sponsors.append(s)
        return sponsors

    def _attach_grant(self, Grant, project, sponsors, *, year):
        """Create one Grant per sponsor and link it to the project."""
        from datetime import date as _date
        for idx, sponsor in enumerate(sponsors):
            grant = Grant.objects.create(
                title=f"Demo Grant: {project.short_name} / {sponsor.short_name} #{idx + 1}",
                sponsor=sponsor,
                date=_date(year, 1, 1),
                funding_amount=100000 * (idx + 1),
                grant_id=f"DEMO-{idx + 1}",
            )
            grant.projects.add(project)

    # --- Project 1: short sidebar, active ----------------------------------

    def _make_demo_active_small(self, Project, ProjectRole, Roles, people):
        proj = Project.objects.create(
            name="Demo Project: Active (Short Sidebar)",
            short_name="demo-active-small",
            start_date=date(2024, 1, 1),
            end_date=None,
            summary="A small active demo project for visual testing of the short-sidebar case.",
            about="This project is intentionally tiny so the sidebar fits in one viewport. Use it to confirm the sticky behavior of a short sidebar on a long page.",
        )
        # 1 active PI, 1 active Student Lead — that's the whole leadership block.
        ProjectRole.objects.create(
            project=proj, person=people["Lovelace"],
            start_date=date(2024, 1, 1), end_date=None,
            lead_project_role=Roles.PI,
        )
        ProjectRole.objects.create(
            project=proj, person=people["Allen"],
            start_date=date(2024, 1, 1), end_date=None,
            lead_project_role=Roles.STUDENT_LEAD,
        )
        self.stdout.write(f"  ✓ demo-active-small             (1 PI + 1 Student Lead, no pubs)")
        return proj

    # --- Project 2: tall sidebar, active -----------------------------------

    def _make_demo_active_tall(self, Project, ProjectRole, Roles, people):
        proj = Project.objects.create(
            name="Demo Project: Active (Tall Sidebar — Sidewalk-like)",
            short_name="demo-active-tall",
            start_date=date(2019, 1, 1),
            end_date=None,
            summary="A large active demo project with lots of current and former members — sidebar exceeds viewport height.",
            about="This project is intentionally large. Use it to confirm sidebar behavior when the sidebar is taller than the viewport. The 'Former Student Lead' and 'Former PI' headers should still include 'Former' because the project itself is active (only individual members' roles ended).",
        )
        # 3 active PIs/Co-PIs
        ProjectRole.objects.create(project=proj, person=people["Lovelace"],
                                   start_date=date(2019, 1, 1), end_date=None,
                                   lead_project_role=Roles.PI)
        ProjectRole.objects.create(project=proj, person=people["Turing"],
                                   start_date=date(2020, 6, 1), end_date=None,
                                   lead_project_role=Roles.CO_PI)
        ProjectRole.objects.create(project=proj, person=people["Hopper"],
                                   start_date=date(2021, 1, 1), end_date=None,
                                   lead_project_role=Roles.CO_PI)
        # 2 inactive (alumni) PIs/Co-PIs
        ProjectRole.objects.create(project=proj, person=people["Knuth"],
                                   start_date=date(2019, 1, 1), end_date=date(2021, 6, 1),
                                   lead_project_role=Roles.PI)
        ProjectRole.objects.create(project=proj, person=people["Wing"],
                                   start_date=date(2019, 6, 1), end_date=date(2022, 1, 1),
                                   lead_project_role=Roles.CO_PI)
        # 3 active Student Leads
        for last in ("Allen", "Babbage", "Curie"):
            ProjectRole.objects.create(project=proj, person=people[last],
                                       start_date=date(2023, 9, 1), end_date=None,
                                       lead_project_role=Roles.STUDENT_LEAD)
        # 5 inactive (alumni) Student Leads
        for last, end in (
            ("Darwin", date(2020, 6, 1)),
            ("Einstein", date(2021, 6, 1)),
            ("Feynman", date(2022, 6, 1)),
            ("Goldberg", date(2022, 12, 1)),
            ("Hamilton", date(2023, 6, 1)),
        ):
            ProjectRole.objects.create(project=proj, person=people[last],
                                       start_date=date(2019, 1, 1), end_date=end,
                                       lead_project_role=Roles.STUDENT_LEAD)
        self.stdout.write(f"  ✓ demo-active-tall              (3 active PIs/Co-PIs + 3 active Student Leads + 5 alumni)")
        return proj

    # --- Project 3: tall sidebar, ENDED ------------------------------------

    def _make_demo_ended_tall(self, Project, ProjectRole, Roles, people):
        # Project ended Jan 2023; all role end_dates well before then so
        # they fall outside the 45-day buffer in get_project_leadership
        # and end up in the inactive lists.
        proj_end = date(2023, 1, 1)
        proj = Project.objects.create(
            name="Demo Project: Ended (Tall Sidebar)",
            short_name="demo-ended-tall",
            start_date=date(2018, 1, 1),
            end_date=proj_end,
            summary="A completed demo project for testing the 'Former-prefix-dropped' branch (#1245).",
            about="The project itself has ended, so per #1245 the sidebar should say 'Student Lead'/'PI'/'Co-PI' WITHOUT the 'Former' prefix — the page header already announces the project is completed.",
        )
        # 2 PIs, 2 Co-PIs (all inactive — roles ended well before project end)
        ProjectRole.objects.create(project=proj, person=people["Lovelace"],
                                   start_date=date(2018, 1, 1), end_date=date(2022, 1, 1),
                                   lead_project_role=Roles.PI)
        ProjectRole.objects.create(project=proj, person=people["Knuth"],
                                   start_date=date(2018, 1, 1), end_date=date(2021, 6, 1),
                                   lead_project_role=Roles.PI)
        ProjectRole.objects.create(project=proj, person=people["Turing"],
                                   start_date=date(2018, 1, 1), end_date=date(2022, 1, 1),
                                   lead_project_role=Roles.CO_PI)
        ProjectRole.objects.create(project=proj, person=people["Wing"],
                                   start_date=date(2018, 1, 1), end_date=date(2021, 6, 1),
                                   lead_project_role=Roles.CO_PI)
        # 6 Student Leads (all inactive)
        for last, end in (
            ("Iverson", date(2020, 6, 1)),
            ("Joliot", date(2021, 1, 1)),
            ("Kepler", date(2021, 6, 1)),
            ("Lamarr", date(2022, 1, 1)),
            ("Allen", date(2022, 6, 1)),
            ("Babbage", date(2022, 9, 1)),
        ):
            ProjectRole.objects.create(project=proj, person=people[last],
                                       start_date=date(2018, 1, 1), end_date=end,
                                       lead_project_role=Roles.STUDENT_LEAD)
        self.stdout.write(f"  ✓ demo-ended-tall               (4 PIs/Co-PIs + 6 Student Leads, all inactive)")
        return proj

    # --- Project 4: tall main, short sidebar -------------------------------

    def _make_demo_tall_main_short_sidebar(self, Project, ProjectRole, Roles, people):
        proj = Project.objects.create(
            name="Demo Project: Tall Main + Short Sidebar",
            short_name="demo-tall-main-short-sidebar",
            start_date=date(2024, 1, 1),
            end_date=None,
            summary="A project with only a few sidebar entries but lots of publications, so the main content is much taller than the sidebar.",
            about="Use this to verify post-sidebar layout behavior: as you scroll the main content past where the sidebar ends, is there a lopsided empty column on the right? With position:sticky kept, the sidebar should remain visible at top:100px while you read the rest of the main column.",
        )
        ProjectRole.objects.create(project=proj, person=people["Lovelace"],
                                   start_date=date(2024, 1, 1), end_date=None,
                                   lead_project_role=Roles.PI)
        ProjectRole.objects.create(project=proj, person=people["Allen"],
                                   start_date=date(2024, 1, 1), end_date=None,
                                   lead_project_role=Roles.STUDENT_LEAD)
        self.stdout.write(f"  ✓ demo-tall-main-short-sidebar  (1 PI + 1 Student Lead, ~15 publications)")
        return proj

    # --- Publications ------------------------------------------------------

    _FORUMS = ["CHI", "ASSETS", "UIST", "CSCW", "IUI", "DIS", "TEI"]

    def _make_demo_publications(self, Publication, project, people, *, count, start_year, end_year):
        """Attach `count` dummy publications to `project`, spread across the given year range."""
        from website.models.publication import PubType
        # Cycle authors so each pub has 1-3 different demo authors
        author_pool = list(people.values())
        years = list(range(start_year, end_year + 1))
        for i in range(count):
            year = years[i % len(years)]
            forum = self._FORUMS[i % len(self._FORUMS)]
            pub = Publication.objects.create(
                title=f"Demo Paper: An Investigation of Demo Phenomenon #{i + 1}",
                date=date(year, ((i * 3) % 12) + 1, 15),
                forum_name=forum,
                pub_venue_type=PubType.CONFERENCE,
                pdf_file=SimpleUploadedFile(
                    f"demo_paper_{i + 1}.pdf",
                    b"%PDF-1.4 demo",
                    content_type="application/pdf",
                ),
            )
            pub.projects.add(project)
            # Rotate 1-3 authors per pub
            n_authors = (i % 3) + 1
            authors = [author_pool[(i + j) % len(author_pool)] for j in range(n_authors)]
            pub.authors.add(*authors)
