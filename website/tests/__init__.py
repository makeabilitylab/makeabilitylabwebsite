"""
Test package for the website app.

Two styles live side by side (see the module docstrings):

- **Unit** — ``SimpleTestCase`` + ``unittest.mock`` for pure logic (formatters,
  BibTeX generation, etc.); no DB, runs in milliseconds.
- **Integration** — ``DatabaseTestCase`` (in ``tests/base.py``) for
  view / queryset / template regressions; each test runs in a transaction that
  is rolled back.

Django auto-discovers any ``test_*.py`` module here, so adding a new test file
needs no registration. Run the suite with the test-settings shim::

    python manage.py test website --settings=makeabilitylab.settings_test
"""
