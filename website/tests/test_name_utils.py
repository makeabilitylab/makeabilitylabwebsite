"""
Unit tests for website.utils.name_utils (pure logic, no DB).

Covers the url_name normalization key and the readable-URL derivation
(``build_unique_url_name``) used by ``Person.save()`` and the
``recompute_url_names`` command for the #1275 dedup / #1206 namesake work.
"""

from django.test import SimpleTestCase

from website.utils.name_utils import (
    build_unique_url_name,
    normalize_person_name,
)


class NormalizePersonNameTests(SimpleTestCase):
    def test_basic_lowercases_and_concatenates(self):
        self.assertEqual(normalize_person_name('Jon', 'Froehlich'), 'jonfroehlich')

    def test_accents_folded_and_punctuation_stripped(self):
        self.assertEqual(normalize_person_name('Renée', "O'Brien"), 'reneeobrien')

    def test_acute_accents_and_cedilla_are_folded_not_dropped(self):
        # Regression for the incomplete hand-rolled accent map (#1275): acute
        # accents and the cedilla were dropped, mangling keys (cludiosilva) and
        # hiding accented-name duplicates. NFKD folds them to ASCII.
        self.assertEqual(normalize_person_name('Cláudio', 'Silva'), 'claudiosilva')
        self.assertEqual(normalize_person_name('Edgar', 'Martínez'), 'edgarmartinez')
        self.assertEqual(normalize_person_name('François', 'Guimbretière'),
                         'francoisguimbretiere')

    def test_accented_namesakes_share_a_key(self):
        # The whole point: "Cláudio Silva" and "Claudio Silva" must cluster.
        self.assertEqual(
            normalize_person_name('Cláudio', 'Silva'),
            normalize_person_name('Claudio', 'Silva'),
        )

    def test_handles_none(self):
        self.assertEqual(normalize_person_name(None, 'Zhang'), 'zhang')


class BuildUniqueUrlNameTests(SimpleTestCase):
    def test_returns_bare_key_when_free(self):
        never_taken = lambda u: False
        self.assertEqual(
            build_unique_url_name('Jasmine', 'Xin', 'Zhang', never_taken),
            'jasminezhang',
        )

    def test_prefers_middle_initial_on_collision(self):
        taken = {'jasminezhang'}.__contains__
        self.assertEqual(
            build_unique_url_name('Jasmine', 'Xin', 'Zhang', taken),
            'jasminexzhang',
        )

    def test_numeric_fallback_when_no_middle_name(self):
        taken = {'jasminezhang'}.__contains__
        self.assertEqual(
            build_unique_url_name('Jasmine', '', 'Zhang', taken),
            'jasminezhang2',
        )

    def test_numeric_fallback_when_middle_initial_also_taken(self):
        taken = {'jasminezhang', 'jasminexzhang'}.__contains__
        self.assertEqual(
            build_unique_url_name('Jasmine', 'Xin', 'Zhang', taken),
            'jasminezhang2',
        )

    def test_numeric_fallback_keeps_incrementing(self):
        taken = {'jasminezhang', 'jasminezhang2', 'jasminezhang3'}.__contains__
        # No middle name, so it must skip past every taken numeric suffix.
        self.assertEqual(
            build_unique_url_name('Jasmine', None, 'Zhang', taken),
            'jasminezhang4',
        )

    def test_middle_initial_is_accent_folded(self):
        # Middle name starting with an accented char folds to its ASCII initial.
        taken = {'jonfroehlich'}.__contains__
        self.assertEqual(
            build_unique_url_name('Jon', 'Über', 'Froehlich', taken),
            'jonufroehlich',
        )
