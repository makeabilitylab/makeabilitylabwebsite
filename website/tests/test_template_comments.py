"""
Mechanical guard for a recurring bug: Django's ``{# … #}`` template comment is
**single-line only**. A ``{# … #}`` that spans multiple lines is NOT tokenized as
a comment — Django renders the whole thing (text and ``#}`` included) as visible
page content. This shipped to prod once, printing a note on every award card
(fixed in 2.14.2). For multi-line comments use ``{% comment %} … {% endcomment %}``.

This is a ``SimpleTestCase`` (no DB), so it runs as part of the normal test suite
in CI (.github/workflows/test.yml) on every push/PR, and locally via
``manage.py test``. See the template-comment note in CLAUDE.md.
"""

from pathlib import Path

from django.test import SimpleTestCase

# Repo root: website/tests/this_file.py -> parents[2].
REPO_ROOT = Path(__file__).resolve().parents[2]
SKIP_DIRS = {".git", "node_modules", "static", "staticfiles", "media",
             ".venv", "venv", "htmlcov", "__pycache__"}


def _template_html_files():
    """Yield every ``*.html`` living under any ``templates/`` directory in the repo."""
    for path in REPO_ROOT.rglob("*.html"):
        if "templates" not in path.parts:
            continue
        if SKIP_DIRS.intersection(path.parts):
            continue
        yield path


def _multiline_comment_lines(text):
    """Return the 1-based line numbers where a ``{#`` opens but doesn't close on
    the same line (i.e. a multi-line ``{# #}`` comment)."""
    bad = []
    for n, line in enumerate(text.splitlines(), 1):
        idx = line.find("{#")
        if idx != -1 and "#}" not in line[idx + 2:]:
            bad.append(n)
    return bad


class TemplateCommentLintTests(SimpleTestCase):
    def test_no_multiline_django_comments(self):
        offenders = []
        for path in _template_html_files():
            text = path.read_text(encoding="utf-8")
            for n in _multiline_comment_lines(text):
                offenders.append(f"{path.relative_to(REPO_ROOT)}:{n}")

        self.assertEqual(
            offenders, [],
            "Multi-line Django `{# #}` comment(s) found — Django renders these as "
            "visible page text. Use `{% comment %}…{% endcomment %}` instead:\n  "
            + "\n  ".join(offenders),
        )

    def test_detector_catches_a_multiline_comment(self):
        # Pin the detection logic itself so the guard can't silently rot.
        self.assertEqual(_multiline_comment_lines("{# one line ok #}\n<p>x</p>"), [])
        self.assertEqual(
            _multiline_comment_lines("<p>x</p>\n{# this opens\n   and closes later #}\n"),
            [2],
        )
