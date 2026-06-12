"""
Auto-generated bio for Makeability Lab Person profile pages.

The bio is composed of up to four sentences, in this order:

  1. Role sentence  - describes the person's relationship to the lab
                      (current member, alumni, collaborator, future joiner, etc.).
  2. Contributions  - projects + publications.
  3. Mentors        - who advised them.
  4. Mentees        - who they advised.

A Person with no Position records AND no publications gets no auto-bio (an
empty string), so the member template's bio block is hidden entirely rather
than fabricating "X will be joining the Makeability Lab" for someone the lab
has no recorded relationship with.

The returned string is HTML (contains <a> tags); the template renders it with
the ``|safe`` filter. Free-text fields (person names, project names) are
escaped before they are spliced into anchor tags.
"""

from django.urls import reverse
from django.utils.html import escape

from website.models import Position
from website.models.position import Role


def auto_generate_bio(person):
    """
    Build an HTML auto-bio for ``person`` from their stored lab data.

    Args:
        person: a Person model instance.

    Returns:
        str: HTML bio, or "" when there is nothing meaningful to say
        (no positions and no publications). The caller should treat the
        empty string as "do not render the bio block".
    """
    role = _role_sentence(person)
    if not role:
        return ""

    sentences = [role]

    contrib = _contributions_sentence(person)
    if contrib:
        sentences.append(contrib)

    mentor = _mentor_sentence(person)
    if mentor:
        sentences.append(mentor)

    mentee = _mentee_sentence(person)
    if mentee:
        sentences.append(mentee)

    return " ".join(sentences)


def _role_sentence(person):
    """
    Build the first sentence describing the person's relationship to the lab.

    Returns ``None`` when no auto-bio should be generated at all - the
    person has no Position records and no publications.
    """
    full_name = escape(person.get_full_name())
    first_name = escape(person.first_name)
    latest_position = person.get_latest_position

    # No Position records at all. We only generate a bio when there is
    # something to anchor it to (publications). Otherwise we return None so
    # the caller can suppress the bio block entirely rather than emit a
    # misleading "will be joining" line for someone with no lab relationship.
    if latest_position is None:
        if person.publication_set.exists():
            return f"{full_name} has published with the Makeability Lab."
        return None

    # Future-only: a real Person scheduled to join, but who hasn't started.
    if not person.has_started:
        start_str = latest_position.start_date.strftime("%b %Y")
        return f"{full_name} will be joining the Makeability Lab on {start_str}."

    if person.is_current_member:
        title = person.get_current_title
        article = Position.get_indefinite_article_for_title(title)
        sentence = (
            f"{full_name} is currently {article} {title} in the Makeability Lab."
        )
        duration_str = _format_member_duration(person)
        if duration_str:
            sentence += f" {first_name} has been in the lab for {duration_str}."
        return sentence

    if person.is_alumni_member:
        # Anchor on the latest MEMBER position, not get_latest_position - a
        # former member who later became a collaborator would otherwise be
        # described as "was a Collaborator (... to present)", which is wrong
        # on two counts (title and end date).
        member_position = _get_latest_member_position(person)
        earliest_member_position = _get_earliest_member_position(person)

        title = member_position.title
        article = Position.get_indefinite_article_for_title(title)
        start = earliest_member_position.start_date.strftime("%b %Y")
        end = (
            member_position.end_date.strftime("%b %Y")
            if member_position.end_date
            else "present"
        )
        duration_str = _format_member_duration(person)
        duration_part = f" for {duration_str}" if duration_str else ""
        sentence = (
            f"{full_name} was {article} {title} in the Makeability Lab"
            f"{duration_part} ({start} to {end})."
        )
        # If the alumni is still active as a collaborator, append that
        # status as a second sentence rather than mangling the first one.
        if person.is_current_collaborator:
            sentence += (
                f" {first_name} is currently a collaborator with "
                f"the Makeability Lab."
            )
        return sentence

    if person.is_current_collaborator:
        return f"{full_name} is a collaborator with the Makeability Lab."

    if person.is_past_collaborator:
        return f"{full_name} was a collaborator with the Makeability Lab."

    return None


def _contributions_sentence(person):
    """
    Build the contributions sentence summarising projects and publication count.

    Up to 3 project names are listed inline; beyond that the count is given
    with "including" + the first three. Publication count is appended as a
    plain count rather than a list.
    """
    projects = sorted(person.get_projects, key=lambda p: p.name)
    proj_count = len(projects)
    pub_count = person.publication_set.count()

    if proj_count == 0 and pub_count == 0:
        return None

    sentence = "They contributed to"

    if proj_count == 1:
        sentence += f" a project called {_project_link(projects[0])}"
    elif proj_count > 1:
        shown_links = [_project_link(p) for p in projects[:3]]
        list_str = _join_with_oxford_comma(shown_links)
        if proj_count <= 3:
            sentence += f" {proj_count} projects: {list_str}"
        else:
            sentence += f" {proj_count} projects, including {list_str}"

    if pub_count > 0:
        plural = "s" if pub_count > 1 else ""
        if proj_count > 0:
            sentence += f", as well as {pub_count} publication{plural}"
        else:
            sentence += f" {pub_count} publication{plural}"

    return sentence + "."


def _mentor_sentence(person):
    """Build the sentence describing who has advised this person."""
    mentors = list(person.get_grad_mentors())
    if not mentors:
        return None

    verb = "is" if person.is_active else "was"
    mentor_links = [_member_link(m) for m in mentors]
    list_str = _join_with_oxford_comma(mentor_links)
    return f"{escape(person.first_name)} {verb} mentored by {list_str}."


def _mentee_sentence(person):
    """
    Build the sentence describing who this person has mentored.

    Up to ``DISPLAY_LIMIT`` mentees are highlighted by name; the underlying
    queryset is randomised so the highlighted three rotate across page loads
    for heavily-mentoring people. The total count is always shown explicitly.
    """
    DISPLAY_LIMIT = 3
    mentees = person.get_mentees(randomize=True)
    mentee_count = mentees.count()
    if mentee_count == 0:
        return None

    first_name = escape(person.first_name)

    # "During their time in the lab" is only accurate for member/alumni -
    # collaborators were never "in the lab" in that sense.
    if person.is_current_member or person.is_alumni_member:
        intro = f"During their time in the lab, {first_name} mentored"
    else:
        intro = f"{first_name} has mentored"

    shown_links = [_member_link(m) for m in mentees[:DISPLAY_LIMIT]]

    if mentee_count == 1:
        return f"{intro} 1 Makeability Lab student, {shown_links[0]}."

    sep = ":" if mentee_count <= DISPLAY_LIMIT else ", including"
    list_str = _join_with_oxford_comma(shown_links)
    return f"{intro} {mentee_count} Makeability Lab students{sep} {list_str}."


# --- small helpers ---------------------------------------------------------


def _join_with_oxford_comma(items):
    """
    Join a list of HTML-safe strings with English-list grammar.

    Examples:
        []                  -> ""
        ["A"]               -> "A"
        ["A", "B"]          -> "A and B"
        ["A", "B", "C"]     -> "A, B, and C"
    """
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return ", ".join(items[:-1]) + f", and {items[-1]}"


def _member_link(person):
    """Return an HTML <a> tag linking to another Person's profile page."""
    url = reverse(
        "website:member_by_name", kwargs={"member_name": person.get_url_name()}
    )
    return f"<a href='{url}'>{escape(person.get_full_name())}</a>"


def _project_link(project):
    """Return an HTML <a> tag linking to a Project page."""
    url = reverse("website:project", kwargs={"project_name": project.short_name})
    return f"<a href='{url}'>{escape(project.name)}</a>"


def _format_member_duration(person):
    """Humanised total time the person has spent as a MEMBER of the lab."""
    total = person.get_total_time_as_member
    if not total:
        return ""
    return humanize_duration(total)


def _get_latest_member_position(person):
    """Most recent MEMBER-role Position for this person, or None."""
    return (
        person.position_set.filter(role=Role.MEMBER).order_by("-start_date").first()
    )


def _get_earliest_member_position(person):
    """Earliest MEMBER-role Position for this person, or None."""
    return (
        person.position_set.filter(role=Role.MEMBER).order_by("start_date").first()
    )


def humanize_duration(duration):
    """
    Format a ``datetime.timedelta`` as a human-readable string.

    Examples:
        timedelta(days=365 * 5)   -> "5.0 years"
        timedelta(days=365 * 1.5) -> "1.5 years"
        timedelta(days=180)       -> "6 months"
        timedelta(days=10)        -> "less than a month"
    """
    total_months = duration.total_seconds() / (30 * 24 * 60 * 60)

    if total_months >= 12:
        years = total_months / 12
        return f"{years:.1f} years"

    if total_months >= 1:
        months_int = round(total_months)
        return f"{months_int} month{'s' if months_int != 1 else ''}"

    return "less than a month"
