"""
Shared utility functions for Django admin customizations.

This module contains reusable queryset builders and helper functions
used across multiple admin classes to maintain DRY principles.

These utilities centralize common filtering logic (e.g., finding active professors
or potential mentors) that would otherwise be duplicated across admin files like
person_admin.py and position_admin.py.
"""

from django.db.models import Q, Case, When, Value, IntegerField
from django.utils import timezone

from website.models import Person, Position
from website.models.position import Title


def get_active_professors_queryset(prioritized_name=("Jon", "Froehlich")):
    """
    Build a queryset of currently active professors, optionally prioritizing a specific person.

    This is used primarily for populating advisor/co-advisor dropdown fields in the
    admin interface, ensuring only currently active professors appear as options.

    Filters to people who:
        - Hold a professor-level title (as defined by Position.get_prof_titles())
        - Have a start date on or before today
        - Have no end date OR have an end date in the future

    Args:
        prioritized_name: Tuple of (first_name, last_name) to sort first in the list.
                          This is useful for placing the lab PI at the top of dropdowns.
                          Set to None to disable prioritization and sort alphabetically.

    Returns:
        QuerySet[Person]: Filtered and ordered Person queryset containing only
                          currently active professors.

    Example:
        >>> # Get all active professors with default prioritization
        >>> professors = get_active_professors_queryset()
        >>> for prof in professors:
        ...     print(prof.get_full_name())

        >>> # Get professors without any prioritization
        >>> professors = get_active_professors_queryset(prioritized_name=None)
    """
    # First, find all Position records that have professor-level titles.
    # Position.get_prof_titles() returns titles like PROFESSOR, ASSOCIATE_PROFESSOR, etc.
    prof_positions = Position.objects.filter(
        title__in=Position.get_prof_titles()
    )

    today = timezone.now().date()

    # Filter Person records to those who:
    # 1. Have a position in our professor positions set
    # 2. Have already started (start_date <= today)
    # 3. Haven't ended yet (end_date is null OR end_date >= today)
    #
    # We use distinct() because a person could have multiple positions
    # that match our criteria, and we only want each person once.
    professors = (
        Person.objects
        .filter(
            Q(position__in=prof_positions),
            Q(position__start_date__lte=today),
            Q(position__end_date__gte=today) | Q(position__end_date__isnull=True)
        )
        .distinct()
    )

    # Optionally prioritize a specific person (typically the lab PI) to appear
    # first in dropdown lists. This improves UX since the PI is the most
    # commonly selected advisor.
    if prioritized_name:
        first_name, last_name = prioritized_name

        # Annotate each record with a custom_order field:
        # - 1 for the prioritized person (appears first)
        # - 2 for everyone else (sorted alphabetically after)
        professors = professors.annotate(
            custom_order=Case(
                When(first_name=first_name, last_name=last_name, then=Value(1)),
                default=Value(2),
                output_field=IntegerField(),
            )
        ).order_by('custom_order', 'first_name')
    else:
        # No prioritization requested; just sort alphabetically by first name
        professors = professors.order_by('first_name')

    return professors


def get_active_mentors_queryset():
    """
    Build a queryset of currently active potential mentors.

    This is used for populating the grad_mentor dropdown field in the admin
    interface. Mentors are typically senior lab members who can guide newer
    students (e.g., undergrads or early MS students).

    Filters to people who:
        - Hold one of the designated mentor-eligible titles
        - Have a start date on or before today
        - Have no end date OR have an end date in the future

    The mentor-eligible titles are:
        - POST_DOC
        - PHD_STUDENT
        - MS_STUDENT
        - RESEARCH_SCIENTIST
        - DIRECTOR
        - SOFTWARE_DEVELOPER
        - DESIGNER

    Returns:
        QuerySet[Person]: Filtered and ordered Person queryset containing only
                          currently active potential mentors, sorted alphabetically
                          by first name.

    Example:
        >>> mentors = get_active_mentors_queryset()
        >>> for mentor in mentors:
        ...     print(f"{mentor.get_full_name()} - {mentor.get_current_title()}")
    """
    # Define which titles qualify someone as a potential mentor.
    # These are typically senior lab members who have enough experience
    # to guide newer students.
    mentor_titles = [
        Title.POST_DOC,
        Title.PHD_STUDENT,
        Title.MS_STUDENT,
        Title.RESEARCH_SCIENTIST,
        Title.DIRECTOR,
        Title.SOFTWARE_DEVELOPER,
        Title.DESIGNER,
    ]

    today = timezone.now().date()

    # Filter Person records to those who:
    # 1. Have a position with one of the mentor-eligible titles
    # 2. Have already started (start_date <= today)
    # 3. Haven't ended yet (end_date is null OR end_date >= today)
    #
    # Results are sorted alphabetically by first name for easy scanning.
    # We use distinct() because a person could have multiple qualifying
    # positions, and we only want each person to appear once.
    return (
        Person.objects
        .filter(
            Q(position__title__in=mentor_titles),
            Q(position__start_date__lte=today),
            Q(position__end_date__gte=today) | Q(position__end_date__isnull=True)
        )
        .order_by('first_name')
        .distinct()
    )