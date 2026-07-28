"""
Wards around the ``Title`` choices on ``Position``.

Adding a title is a three-place edit: the enum member, ``TITLE_ORDER_MAPPING``
(``get_sorted_titles`` raises ``KeyError`` for a title missing from the map), and
whichever ``is_*_position`` bucket the title belongs to (that bucket drives the
abstracted-title grouping used by the people pages). These tests pin all three so
the next title added doesn't silently land half-wired.
"""

from django.test import SimpleTestCase

from website.models import Position
from website.models.position import AbstractedTitle, Title


class TitleOrderMappingTests(SimpleTestCase):
    def test_every_title_has_an_order(self):
        """Every Title needs an order entry or get_sorted_titles() blows up."""
        missing = [t for t in Title if t not in Position.TITLE_ORDER_MAPPING]
        self.assertEqual(missing, [], f"Titles missing from TITLE_ORDER_MAPPING: {missing}")

    def test_get_sorted_titles_covers_all_titles(self):
        self.assertEqual(set(Position.get_sorted_titles()), set(Title))

    def test_orders_are_unique(self):
        orders = list(Position.TITLE_ORDER_MAPPING.values())
        self.assertEqual(len(orders), len(set(orders)), "duplicate order values")


class ResearchSoftwareEngineerTitleTests(SimpleTestCase):
    """The Research Software Engineer title (added alongside Research Scientist)."""

    def test_title_choice_exists(self):
        self.assertEqual(Title.RESEARCH_SOFTWARE_ENGINEER, "Research Software Engineer")
        self.assertIn(("Research Software Engineer", "Research Software Engineer"), Title.choices)

    def test_fits_in_the_title_column(self):
        max_length = Position._meta.get_field("title").max_length
        self.assertLessEqual(len(Title.RESEARCH_SOFTWARE_ENGINEER.value), max_length)

    def test_sorts_just_after_research_scientist(self):
        sorted_titles = Position.get_sorted_titles()
        self.assertEqual(
            sorted_titles.index(Title.RESEARCH_SOFTWARE_ENGINEER),
            sorted_titles.index(Title.RESEARCH_SCIENTIST) + 1,
        )

    def test_is_a_professional_position(self):
        """Both the str and Position forms — they're separate code paths."""
        self.assertTrue(Position.is_professional_position(Title.RESEARCH_SOFTWARE_ENGINEER.value))
        self.assertTrue(
            Position.is_professional_position(Position(title=Title.RESEARCH_SOFTWARE_ENGINEER.value))
        )

    def test_abstracts_to_professional(self):
        # Use the raw str, as a Position loaded from the DB would carry.
        self.assertEqual(
            Position.get_abstracted_title(Position(title=Title.RESEARCH_SOFTWARE_ENGINEER.value)),
            AbstractedTitle.PROFESSIONAL.value,
        )
