"""
Idempotent importer for the Awards page (#awards-update).

Backfills the people / project / faculty *distinctions* that were missing from
the Award table (sourced from the news archive + Jon's CV; see
docs/plans/awards-content-audit.md). Paper awards are intentionally NOT here —
those live on ``Publication.award`` and are already set (the lone exception,
"Playing on Hard Mode", is tracked as a separate issue).

Design:
  * Idempotent. Each award is keyed by (title, date); an existing match is left
    untouched (so manual admin edits win) and only missing ones are created.
    Safe to run on every container start, like the other one-shot commands in
    docker-entrypoint.sh.
  * Recipients/projects are resolved by name against the live DB. A name that
    doesn't resolve is logged as a warning and skipped; the award is still
    created with whatever honorees did resolve (so a renamed person never blocks
    the rest of the import).
  * ``--dry-run`` reports what would happen without writing.

Editors: to drop an award you don't want, delete its dict from ENTRIES before
this ships (nothing deploys until the branch merges). Items flagged ``# REVIEW``
are lower-confidence (date/venue/recipient guessed) — confirm or trim them.
"""

from datetime import date

from django.core.management.base import BaseCommand
from django.db import transaction

from website.models import Award, Person, Project
from website.models.award import AwardType

NEWS = "https://makeabilitylab.cs.washington.edu/news/"

# Each entry: title, organization, date, award_type, url, description,
# recipients (list of "First Last" — matched to Person), projects (list of
# Project.name). Recipients use the EXACT stored name (e.g. Daniel's surname is
# "Zamora", first name "Daniel Campos").
ENTRIES = [
    # ---- Faculty Honors ----------------------------------------------------
    dict(title="NSF CAREER Award", organization="National Science Foundation",
         date=date(2017, 2, 14), award_type=AwardType.FACULTY_HONOR,
         url=NEWS + "nsf-career-award/",
         description="A Tangible-Graphical Approach to Engage Young Children in Wearable Design.",
         recipients=["Jon Froehlich"], projects=[]),
    dict(title="Google Faculty Research Award", organization="Google",
         date=date(2013, 1, 1), award_type=AwardType.FACULTY_HONOR, url=None,
         description="For “Combining Crowdsourcing and Computer Vision for Street-level Accessibility.”",
         recipients=["Jon Froehlich"], projects=["Project Sidewalk"]),  # REVIEW: CV says 2012; Grants DB says 2013
    dict(title="Google Faculty Research Award", organization="Google",
         date=date(2017, 2, 15), award_type=AwardType.FACULTY_HONOR,
         url=NEWS + "google-faculty-award-on-glassear/",
         description="For “Wearable Sound Awareness Support for the Deaf and Hard of Hearing” (Project GlassEar).",
         recipients=["Jon Froehlich", "Leah Findlater"], projects=["GlassEar"]),
    dict(title="Google Faculty Research Award", organization="Google",
         date=date(2020, 2, 1), award_type=AwardType.FACULTY_HONOR, url=None,
         description="For “Transforming How Blind and Low Vision Developers Design and Implement User Interfaces.”",
         recipients=["Jon Froehlich"], projects=[]),  # REVIEW: not in Grants DB; consider adding there too
    dict(title="Google Faculty Research Award", organization="Google",
         date=date(2024, 10, 1), award_type=AwardType.FACULTY_HONOR,
         url=NEWS + "society-centered-ai-google-research-award/",
         description="Society-Centered AI Research Award for “Exploring AI-Enhanced Mixed-Ability Social Interactions.”",
         recipients=["Jon Froehlich", "Jacob Wobbrock", "Dhruv Jain", "Arnavi Chheda-Kothary"], projects=[]),
    dict(title="3M Non-Tenured Faculty Award", organization="3M",
         date=date(2013, 1, 1), award_type=AwardType.FACULTY_HONOR, url=None,
         description="Using Machine Learning and Intelligent Sensing to Promote Activity Awareness and Modification.",
         recipients=["Jon Froehlich"], projects=[]),  # REVIEW: found in Grants DB; not on the CV list you sent
    dict(title="Inventors in our Midst", organization="1st DC-area Maker Faire",
         date=date(2013, 9, 29), award_type=AwardType.FACULTY_HONOR, url=None,
         description="One of four recognized at the inaugural DC-area Maker Faire.",
         recipients=["Jon Froehlich"], projects=[]),  # REVIEW: CV only

    # ---- PhD Fellowships ---------------------------------------------------
    dict(title="NSF Graduate Research Fellowship", organization="National Science Foundation",
         date=date(2026, 4, 13), award_type=AwardType.PHD_FELLOWSHIP,
         url=NEWS + "two-alums-receive-nsf-grfp/", description=None,
         recipients=["Michael Duan", "Ritesh Kanchi"], projects=[]),
    dict(title="Google-CMD-IT LEAP Alliance Fellowship", organization="Google / CMD-IT",
         date=date(2021, 8, 5), award_type=AwardType.PHD_FELLOWSHIP,
         url=NEWS + "dhruv-jain-selected-for-google-cmd-it-leap-alliance-fellowship/", description=None,
         recipients=["Dhruv Jain"], projects=[]),
    dict(title="All-S.T.A.R. Fellow", organization="NSF All-S.T.A.R. Program",
         date=date(2017, 4, 25), award_type=AwardType.PHD_FELLOWSHIP,
         url=NEWS + "matt-mauriello-selected-as-all-star-fellow/", description=None,
         recipients=["Matthew Mauriello"], projects=[]),
    dict(title="Precourt Center Fellow", organization="Behavior, Energy and Climate Change Conference (BECC)",
         date=date(2009, 1, 1), award_type=AwardType.PHD_FELLOWSHIP, url=None, description=None,
         recipients=["Jon Froehlich"], projects=[]),  # REVIEW: CV only

    # ---- Student Awards ----------------------------------------------------
    dict(title="CRA Outstanding Undergraduate Researcher Award — Honorable Mention",
         organization="Computing Research Association", date=date(2024, 12, 18),
         award_type=AwardType.STUDENT_AWARD,
         url=NEWS + "ritesh-earns-honorable-mention-for-cra-outstanding-undergraduate-researcher/",
         description=None, recipients=["Ritesh Kanchi"], projects=[]),
    dict(title="ACM Student Research Competition — Winner", organization="ACM Richard Tapia Conference",
         date=date(2024, 9, 20), award_type=AwardType.STUDENT_AWARD,
         url=NEWS + "daniel-wins-acm-student-research-competition-at-the-tapia-conference/",
         description=None, recipients=["Daniel Campos Zamora"], projects=[]),
    dict(title="CRA Outstanding Undergraduate Researcher Award", organization="Computing Research Association",
         date=date(2022, 12, 16), award_type=AwardType.STUDENT_AWARD,
         url=NEWS + "congrats-michael-duan-for-cra-undergrad-award/",
         description=None, recipients=["Michael Duan"], projects=[]),
    dict(title="Bob Bandes Memorial Teaching Award — Honorable Mention",
         organization="UW Allen School of Computer Science & Engineering", date=date(2021, 6, 14),
         award_type=AwardType.STUDENT_AWARD,
         url=NEWS + "liang-he-receives-bob-bandes-memorial-honorable-mention-teaching-award/",
         description=None, recipients=["Liang He"], projects=[]),
    dict(title="National SWE Scholarship", organization="Society of Women Engineers",
         date=date(2019, 6, 11), award_type=AwardType.STUDENT_AWARD,
         url=NEWS + "aileen-awarded-national-swe-scholarship/",
         description=None, recipients=["Aileen Zeng"], projects=[]),
    dict(title="Mary Gates Research Scholarship", organization="University of Washington",
         date=date(2019, 3, 13), award_type=AwardType.STUDENT_AWARD,
         url=NEWS + "aileen-zeng-awarded-mary-gates-research-scholarship/",
         description=None, recipients=["Aileen Zeng"], projects=[]),
    dict(title="Google Lime Scholarship", organization="Google",
         date=date(2019, 3, 1), award_type=AwardType.STUDENT_AWARD,
         url=NEWS + "venkatesh-receives-google-lime-scholarship/",
         description=None, recipients=["Venkatesh Potluri"], projects=[]),
    dict(title="ACM-W Scholarship", organization="ACM-W",
         date=date(2016, 3, 1), award_type=AwardType.STUDENT_AWARD,
         url=NEWS + "acm-w-scholarship-to-attend-chi-2016/",
         description=None, recipients=["Manaswi Saha"], projects=[]),
    dict(title="Graduate School Distinguished Dissertation Award", organization="University of Washington",
         date=date(2012, 6, 1), award_type=AwardType.STUDENT_AWARD, url=None,
         description=None, recipients=["Jon Froehlich"], projects=[]),  # REVIEW: CV only
    dict(title="CGS/ProQuest Distinguished Dissertation Award — Honorable Mention",
         organization="Council of Graduate Schools / ProQuest", date=date(2012, 1, 1),
         award_type=AwardType.STUDENT_AWARD, url=None,
         description="In Mathematics, Physical Sciences, and Engineering.",
         recipients=["Jon Froehlich"], projects=[]),  # REVIEW: CV only

    # ---- Project Awards ----------------------------------------------------
    dict(title="Smart City Hub Switzerland Award", organization="Smart City Hub Switzerland",
         date=date(2024, 12, 15), award_type=AwardType.PROJECT_AWARD,
         url=NEWS + "zuriact-with-project-sidewalk-win-smart-city-hub-switzerland-award-2024/",
         description="Awarded to ZüriACT, which builds on Project Sidewalk.",
         recipients=[], projects=["Project Sidewalk"]),
    dict(title="People’s Choice Award", organization=None,
         date=date(2024, 10, 29), award_type=AwardType.PROJECT_AWARD,
         url=NEWS + "altgeoviz-receives-people-choice-award/",
         description=None, recipients=["Chu Li"], projects=["AltGeoViz"]),  # REVIEW: confirm venue/organization
    dict(title="People’s Choice Award", organization=None,
         date=date(2019, 11, 20), award_type=AwardType.PROJECT_AWARD,
         url=NEWS + "homesound-wins-peoples-choice-award/",
         description=None, recipients=["Dhruv Jain"], projects=["HomeSound"]),
    dict(title="People’s Choice Award", organization="UW Allen School Annual Research Day",
         date=date(2018, 11, 2), award_type=AwardType.PROJECT_AWARD,
         url=NEWS + "ar-captioning-wins-the-peoples-choice-award-in-allen-school-annual-research-day/",
         description=None, recipients=["Dhruv Jain"], projects=["AR Captioning"]),
    dict(title="Facilitators’ Choice Award, NSF STEM Video Showcase",
         organization="NSF STEM for All Video Showcase", date=date(2016, 5, 1),
         award_type=AwardType.PROJECT_AWARD, url=None,
         description="Awarded to 13 of 156 video submissions (8.3%).",
         recipients=[], projects=["BodyVis"]),
    dict(title="Madrona Innovation Prize", organization="Allen School Industry Affiliates",
         date=date(2019, 10, 1), award_type=AwardType.PROJECT_AWARD, url=None,
         description=None, recipients=["Dhruv Jain"], projects=["HomeSound"]),  # REVIEW: date/recipient guessed
]


class Command(BaseCommand):
    help = ("Idempotently import the people/project/faculty awards backfilled from the "
            "news archive + CV (see docs/plans/awards-content-audit.md). Safe to re-run.")

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true",
                            help="Report what would change without writing to the DB.")

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        created = skipped = 0

        with transaction.atomic():
            for entry in ENTRIES:
                if Award.objects.filter(title=entry["title"], date=entry["date"]).exists():
                    self.stdout.write(f"  skip (exists): {entry['title']} ({entry['date'].year})")
                    skipped += 1
                    continue

                people = self._resolve_people(entry["recipients"])
                projects = self._resolve_projects(entry["projects"])
                if not people and not projects:
                    self.stderr.write(self.style.WARNING(
                        f"  SKIP (no honorees resolved): {entry['title']} ({entry['date'].year})"))
                    continue

                self.stdout.write(self.style.SUCCESS(
                    f"  create: {entry['title']} ({entry['date'].year}) "
                    f"-> {[p.get_full_name() for p in people] + [pr.name for pr in projects]}"))
                created += 1
                if dry_run:
                    continue

                award = Award.objects.create(
                    title=entry["title"], organization=entry["organization"],
                    date=entry["date"], award_type=entry["award_type"],
                    url=entry["url"], description=entry["description"])
                if people:
                    award.recipients.set(people)
                if projects:
                    award.projects.set(projects)

            fixed = self._fix_facilitators_choice(dry_run)

            if dry_run:
                self.stdout.write(self.style.WARNING("DRY RUN — rolling back."))
                transaction.set_rollback(True)

        self.stdout.write(self.style.SUCCESS(
            f"import_awards done: {created} created, {skipped} skipped, "
            f"{fixed} existing row(s) fixed{' (dry run)' if dry_run else ''}."))

    def _resolve_people(self, names):
        """Resolve "First Last" names to Person rows, warning on any miss."""
        people = []
        for name in names:
            first, _, last = name.rpartition(" ")
            person = Person.objects.filter(first_name=first, last_name=last).first()
            if person:
                people.append(person)
            else:
                self.stderr.write(self.style.WARNING(f"    ! person not found: {name!r}"))
        return people

    def _resolve_projects(self, names):
        projects = []
        for name in names:
            project = Project.objects.filter(name=name).first()
            if project:
                projects.append(project)
            else:
                self.stderr.write(self.style.WARNING(f"    ! project not found: {name!r}"))
        return projects

    def _fix_facilitators_choice(self, dry_run):
        """Data fix (#audit-F): the existing 'Facilitators' Choice' row is dated 2020
        but its '8.7%' description + news confirm it's the 2019 PrototypAR award.
        Correct the date and attach the project/recipient. Idempotent: once the
        date is 2019 it no longer matches the 2020 filter."""
        stale = Award.objects.filter(award_type=AwardType.PROJECT_AWARD,
                                     title__istartswith="Facilitators",
                                     date__year=2020).first()
        if not stale:
            return 0
        self.stdout.write(self.style.SUCCESS(
            f"  fix: '{stale.title}' 2020 -> 2019-05-31 + attach PrototypAR"))
        if dry_run:
            return 1
        stale.date = date(2019, 5, 31)
        stale.save()
        project = Project.objects.filter(name="PrototypAR").first()
        if project:
            stale.projects.add(project)
        person = Person.objects.filter(first_name="Seokbin", last_name="Kang").first()
        if person:
            stale.recipients.add(person)
        return 1
