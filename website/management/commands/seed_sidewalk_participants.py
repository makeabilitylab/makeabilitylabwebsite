"""
Backfills Project Sidewalk contributors recorded in the NSF Crowd+AI annual
project reports (award #2125087, Years 1-4 = Oct 2021 - Sep 2025).

Why this exists: Project Sidewalk now consumes
``/api/v1/projects/sidewalk/people/`` as its single source of truth for who
contributed to PS. That endpoint is driven by :class:`ProjectRole` rows, so a
contributor without one is invisible to Sidewalk even if they have a member
page. Diffing the four NSF participant spreadsheets against the live API turned
up two gaps:

1. Ten people had a member page but no Sidewalk ``ProjectRole`` (mostly UW
   undergrads from Year 1, plus the faculty/collaborators).
2. Seventeen people had no ``Person`` record at all -- every one of them from
   the UIC subaward (Eisenberg / Labbe / Hammel's team).

There is no shell or DB access on the test/prod servers, so this ships as a
one-shot management command wired into ``docker-entrypoint.sh`` -- the same
pattern as ``seed_project_aliases`` (#944), which this is modelled on.

**Create-only, never update.** Re-running is a no-op: the command will not
modify an existing ``Person``, will not add a ``Position`` to anyone who
already has one, and will not touch an existing ``ProjectRole``. That matters
because it runs on *every* container start, long after editors have hand-tuned
these records in ``/admin``.

Dates come from the NSF reporting periods (Oct 1 - Sep 30), which is the finest
granularity the spreadsheets provide -- they record which annual report a person
appeared in, not the day they started. Where someone appeared in consecutive
reports the span is merged into a single role.

Headshots are deliberately out of scope: ``Person.save()`` assigns a random Star
Wars fallback image, and real headshots get uploaded through ``/admin`` so the
Cropper.js crop box (#1299) is set at the same time.

Usage::

    python manage.py seed_sidewalk_participants
    python manage.py seed_sidewalk_participants --dry-run
"""

import logging
from datetime import date

from django.core.management.base import BaseCommand

from website.models import Person, Position, Project, ProjectRole
from website.models.position import Role, Title

_logger = logging.getLogger(__name__)

# The Sidewalk project's URL slug. Resolved case-insensitively, matching how
# views/project.py looks projects up.
SIDEWALK_SLUG = 'sidewalk'

# Affiliation strings for the UIC subaward. These match the existing records for
# Yochai Eisenberg, Delphine Labbe, and Joy Hammel exactly -- keep them in sync
# so the People page groups everyone under one school name.
UIC = 'University of Illinois Chicago'
UIC_DHD = 'Disability and Human Development'
UIC_CS = 'Computer Science'

# Sentinel for a title we genuinely don't know yet. The NSF spreadsheets only
# record "Graduate Student (research assistant)", which doesn't distinguish MS
# from PhD, and the site's Title vocabulary requires that distinction. Entries
# carrying this are SKIPPED rather than guessed: a wrong title publishes to a
# public member page, and no one else on the site uses Title.UNKNOWN, so a
# placeholder would stand out as a mistake. Fill these in as the degree programs
# are confirmed (they're being collected alongside headshots) and the next
# deploy picks them up.
UNRESOLVED = None


def _uic(first, last, email, title, start, end, contribution, department=UIC_DHD,
         positions=None):
    """Build a seed entry for a UIC collaborator (new Person + Position + role).

    All UIC participants are Collaborators rather than Members -- they worked on
    Sidewalk through the subaward, not out of the Makeability Lab.

    Most people held one title for their whole span, so ``title``/``start``/
    ``end`` build a single Position. Pass ``positions`` as a list of
    ``(title, start, end)`` tuples instead for anyone whose title changed
    mid-grant (e.g. an undergrad who started a doctorate).
    """
    if positions is None:
        positions = [(title, start, end)]
    return {
        'first_name': first,
        'last_name': last,
        'email': email,
        'positions': [
            {
                'title': t,
                'role': Role.COLLABORATOR,
                'school': UIC,
                'department': department,
                'start_date': s,
                'end_date': e,
            }
            for t, s, e in positions
        ],
        'project_roles': [(start, end, contribution)],
    }


def _link_only(first, last, start, end, contribution):
    """Build a seed entry for someone who already has a Person *and* Position.

    Only the Sidewalk ``ProjectRole`` is missing, so ``positions`` is empty and
    the command leaves their existing records completely alone.
    """
    return {
        'first_name': first,
        'last_name': last,
        'email': None,
        'positions': [],
        'project_roles': [(start, end, contribution)],
    }


# NSF reporting periods, for reference when reading the dates below:
#   Y1 2021-10-01 -> 2022-09-30    Y3 2023-10-01 -> 2024-09-30
#   Y2 2022-10-01 -> 2023-09-30    Y4 2024-10-01 -> 2025-09-30
PARTICIPANTS = [
    # ---------------------------------------------------------------------
    # Already on the site with a Position -- only the ProjectRole is missing.
    # ---------------------------------------------------------------------
    _link_only(
        'Jeffrey', 'Heer', date(2021, 10, 1), date(2025, 9, 30),
        "Faculty collaborator. Mentored Manaswi Saha and advised on the CHI'22 "
        "paper “Visualizing Urban Accessibility: Investigating "
        "Multi-Stakeholder Perspectives through a Map-based Design Probe "
        "Study”."),
    _link_only(
        'Maryam', 'Hosseini', date(2021, 10, 1), date(2025, 9, 30),
        "Collaborator on computer vision techniques for sidewalk inference. "
        "Co-author on the CVPR'22 workshop paper “Towards Global-Scale "
        "Crowd+AI Techniques to Map and Assess Sidewalks for People with "
        "Disabilities” and the ASSETS'22 poster, and a co-organizer of the "
        "UrbanAccess workshop."),
    _link_only(
        'Zhihan', 'Zhang', date(2022, 10, 1), date(2025, 9, 30),
        "Collaborator on LabelAId and, with Chu Li, on the Infera project for "
        "AI-assisted labeling."),
    _link_only(
        'Johnson', 'Kuang', date(2021, 10, 1), date(2022, 9, 30),
        "Developed the computer vision system and experiments. Fourth author on "
        "the ASSETS'22 poster “Scaling Crowd+AI Sidewalk Accessibility "
        "Assessments”."),
    _link_only(
        'Logan', 'Milandin', date(2021, 10, 1), date(2022, 9, 30),
        "Developed the computer vision system and experiments. Third author on "
        "the ASSETS'22 poster “Scaling Crowd+AI Sidewalk Accessibility "
        "Assessments”."),
    _link_only(
        'Sidharth', 'Lakshmanan', date(2021, 10, 1), date(2022, 9, 30),
        "Coded and tested features in Project Sidewalk with Mikey Saugstad."),
    _link_only(
        'Duanhao', 'Zhang', date(2021, 10, 1), date(2022, 9, 30),
        "MHCI+D design student. Worked on visual designs for Project Sidewalk."),
    _link_only(
        'Alex', 'Liu', date(2023, 10, 1), date(2024, 9, 30),
        "Undergraduate researcher on Project Sidewalk."),
    _link_only(
        'Peyton', 'Rapo', date(2023, 10, 1), date(2024, 9, 30),
        "Undergraduate researcher on Project Sidewalk."),
    _link_only(
        'Bella', 'Buchanan', date(2024, 10, 1), date(2025, 9, 30),
        "Coded and tested features in Project Sidewalk with Mikey Saugstad."),

    # ---------------------------------------------------------------------
    # UIC subaward -- new Person + Position + ProjectRole.
    # ---------------------------------------------------------------------
    _uic('Fabio', 'Miranda', 'fabiom@uic.edu', Title.ASSISTANT_PROF,
         date(2021, 10, 1), date(2025, 9, 30),
         "Faculty collaborator. Consulted on the CVPR'22 workshop paper "
         "“Towards Global-Scale Crowd+AI Techniques to Map and Assess "
         "Sidewalks for People with Disabilities” and helped organize the "
         "UrbanAccess'24 workshop.",
         department=UIC_CS),
    _uic('Sierra', 'Berquist', 'sberqu2@uic.edu', Title.MS_STUDENT,
         date(2021, 10, 1), date(2022, 9, 30),
         "Led communication with partners to organize the advisory board and "
         "recruit new members, and helped recruit for and run the workshop "
         "series."),
    _uic('Fiona', 'Kennedy', 'fkenne2@uic.edu', Title.MS_STUDENT,
         date(2021, 10, 1), date(2022, 9, 30),
         "Developed relationships with local governments and disability "
         "organizations in prospective deployment communities, and created "
         "outreach materials to build stakeholder interest."),
    _uic('Molly', 'Delaney', 'mdelan9@uic.edu', Title.MS_STUDENT,
         date(2022, 10, 1), date(2024, 9, 30),
         "Worked with Devon Snyder and Yochai Eisenberg on events and "
         "trainings, and helped develop the service learning curriculum."),
    # Two positions: the NSF sheets called her a Graduate Student in Y2 and an
    # Undergraduate in Y3, which is backwards. She was an undergrad through May
    # 2024 and started UIC's Occupational Therapy Doctorate in Aug 2024, so the
    # Y2 entry was the error.
    _uic('Lauren', 'Frame', 'lfram2@uic.edu',
         None,  # `title` unused -- superseded by the explicit `positions` below
         date(2022, 10, 1), date(2024, 9, 30),
         "Worked with Devon Snyder and Yochai Eisenberg on Chicago-based "
         "sidewalk auditing projects, and served as a part-time project "
         "coordinator for Project Sidewalk from May to August 2024.",
         positions=[
             (Title.UGRAD, date(2022, 10, 1), date(2024, 5, 31)),
             (Title.PHD_STUDENT, date(2024, 8, 1), date(2024, 9, 30)),
         ]),
    _uic('Abril', 'Martinez', 'amart286@uic.edu', Title.UGRAD,
         date(2022, 10, 1), date(2023, 9, 30),
         "Worked with Devon Snyder and Yochai Eisenberg on a sidewalk auditing "
         "project in Chicago."),
    _uic('Molly', 'McCaffrey', 'mmccaf2@uic.edu', Title.UGRAD,
         date(2022, 10, 1), date(2023, 9, 30),
         "Worked with Devon Snyder and Yochai Eisenberg on a sidewalk auditing "
         "project in Chicago."),
    _uic('Mariana', 'Roa', 'mroa4@uic.edu', Title.UGRAD,
         date(2022, 10, 1), date(2023, 9, 30),
         "Worked with Devon Snyder and Yochai Eisenberg on a sidewalk auditing "
         "project in Chicago."),
    _uic('Juan', 'Rosendo', 'jrose34@uic.edu', Title.UGRAD,
         date(2022, 10, 1), date(2025, 9, 30),
         "Worked on Chicago sidewalk auditing with Devon Snyder and Yochai "
         "Eisenberg, then with Sajad Askari on a validation study examining the "
         "relationship between neighborhood socioeconomic status and sidewalk "
         "issues."),
    _uic('Mackenzie', 'Hayes', 'mhayes28@uic.edu', Title.MS_STUDENT,
         date(2023, 10, 1), date(2024, 9, 30),
         "Supported implementation with local government agencies, ran "
         "mapathons, and supported new community deployments."),
    _uic('Neydi', 'Aparicio', 'napar2@uic.edu', Title.UGRAD,
         date(2023, 10, 1), date(2024, 9, 30),
         "Supported the project's Chicago deployments through auditing on "
         "Project Sidewalk and recruiting for the service learning curriculum."),
    _uic('Sajad', 'Askari', 'saskar6@uic.edu', Title.PHD_STUDENT,
         date(2023, 10, 1), date(2025, 9, 30),
         "Worked on several papers analyzing Project Sidewalk data and "
         "comparing it to other datasets."),
    _uic('Jaimee', 'VanAssche', 'jphipp3@uic.edu', Title.MS_STUDENT,
         date(2023, 10, 1), date(2025, 9, 30),
         "Advanced the service learning curriculum, recruited teachers for the "
         "pilot, evaluated it, and wrote a manuscript on the evaluation."),
    _uic('KiAnna', 'Mckee-Steen', 'kmcke6@uic.edu', Title.PROJECT_COORDINATOR,
         date(2023, 10, 1), date(2025, 9, 30),
         "Produced a promotional video for the project through a capstone "
         "course, then served as project coordinator for the service learning "
         "and Chicago activities, managing curriculum development, IRB, and "
         "teacher recruitment."),
    _uic('Braydon', 'Duplessis', 'bdupl@uic.edu', Title.UGRAD,
         date(2024, 10, 1), date(2025, 9, 30),
         "Worked with Yochai Eisenberg on Chicago-based sidewalk auditing "
         "projects."),
    _uic('Sylvia', 'Waechter', 'swaec2@uic.edu', Title.UGRAD,
         date(2024, 10, 1), date(2025, 9, 30),
         "Worked with Yochai Eisenberg on Chicago-based sidewalk auditing "
         "projects, developed guides for community users doing analysis and "
         "mapping, and supported using Project Sidewalk for ADA transition "
         "plans."),
    _uic('Adamaris', 'Diaz', 'adiaz239@uic.edu', Title.UGRAD,
         date(2024, 10, 1), date(2025, 9, 30),
         "Worked with Yochai Eisenberg on Chicago-based sidewalk auditing "
         "projects and supported recruitment for the service learning program."),
]


class Command(BaseCommand):
    help = ("Idempotently backfills Person/Position/ProjectRole records for Project "
            "Sidewalk contributors listed in the NSF Crowd+AI annual reports (Y1-Y4), "
            "so they appear in /api/v1/projects/sidewalk/people/.")

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run', action='store_true',
            help="Log what would be created without writing anything.")

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        project = Project.objects.filter(short_name__iexact=SIDEWALK_SLUG).first()
        if project is None:
            _logger.warning(
                f"seed_sidewalk_participants: no project with slug "
                f"'{SIDEWALK_SLUG}'; nothing to do.")
            self.stdout.write("seed_sidewalk_participants: Sidewalk project not found; skipped.")
            return

        people_created = positions_created = roles_created = 0
        skipped_unresolved = []

        for entry in PARTICIPANTS:
            first, last = entry['first_name'], entry['last_name']
            specs = entry['positions']

            # Hold back anyone whose title we haven't confirmed rather than
            # publishing a guess (see UNRESOLVED above). All-or-nothing: a
            # person with any unconfirmed title is skipped entirely, so we never
            # leave a half-built record behind.
            if any(spec['title'] is UNRESOLVED for spec in specs):
                skipped_unresolved.append(f"{first} {last}")
                continue

            person = Person.objects.filter(
                first_name__iexact=first, last_name__iexact=last).first()

            if person is None:
                if not specs:
                    # A link-only entry whose Person has vanished (renamed,
                    # merged, deleted). Don't invent a new record -- flag it.
                    _logger.warning(
                        f"seed_sidewalk_participants: expected existing Person "
                        f"'{first} {last}' not found; skipping.")
                    continue
                if dry_run:
                    # Nothing is written, so there's no Person to hang a
                    # Position or roles on. Count what *would* be created and
                    # move to the next entry.
                    _logger.info(
                        f"seed_sidewalk_participants: WOULD create Person, "
                        f"{len(specs)} Position(s), and "
                        f"{len(entry['project_roles'])} ProjectRole(s) for {first} {last}")
                    people_created += 1
                    positions_created += len(specs)
                    roles_created += len(entry['project_roles'])
                    continue
                person = Person.objects.create(
                    first_name=first, last_name=last, email=entry['email'])
                _logger.info(f"seed_sidewalk_participants: created Person {person.get_full_name()}")
                people_created += 1

            # Position must exist before the ProjectRole: Position.save() closes
            # open ProjectRoles for anyone with no active position, and we want
            # that pass to happen before the role rows land.
            if specs:
                if Position.objects.filter(person=person).exists():
                    _logger.info(
                        f"seed_sidewalk_participants: {first} {last} already has a "
                        f"Position; leaving it alone.")
                else:
                    for spec in specs:
                        if dry_run:
                            _logger.info(
                                f"seed_sidewalk_participants: WOULD create "
                                f"{spec['title']} Position for {first} {last}")
                        else:
                            Position.objects.create(person=person, **spec)
                            _logger.info(
                                f"seed_sidewalk_participants: created "
                                f"{spec['title']} Position for {first} {last}")
                        positions_created += 1

            for start_date, end_date, role_text in entry['project_roles']:
                exists = ProjectRole.objects.filter(
                    person=person, project=project, start_date=start_date).exists()
                if exists:
                    _logger.info(
                        f"seed_sidewalk_participants: {first} {last} already has a "
                        f"Sidewalk role starting {start_date}; skipping.")
                    continue
                if dry_run:
                    _logger.info(
                        f"seed_sidewalk_participants: WOULD create ProjectRole for "
                        f"{first} {last} ({start_date} to {end_date})")
                else:
                    ProjectRole.objects.create(
                        person=person, project=project, start_date=start_date,
                        end_date=end_date, role=role_text)
                    _logger.info(
                        f"seed_sidewalk_participants: created ProjectRole for "
                        f"{first} {last} ({start_date} to {end_date})")
                roles_created += 1

        if skipped_unresolved:
            # Loud on purpose: these people are missing from the API until
            # someone fills in their title.
            _logger.warning(
                f"seed_sidewalk_participants: {len(skipped_unresolved)} participant(s) "
                f"held back pending a confirmed title: {', '.join(skipped_unresolved)}")

        prefix = "seed_sidewalk_participants (dry run):" if dry_run else "seed_sidewalk_participants:"
        self.stdout.write(
            f"{prefix} {people_created} people, {positions_created} positions, "
            f"{roles_created} project roles created; "
            f"{len(skipped_unresolved)} held back pending a title.")
