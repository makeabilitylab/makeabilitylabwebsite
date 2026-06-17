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
