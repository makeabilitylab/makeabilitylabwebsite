"""
Regression test for the news crop aspect-ratio contract.

Bug this pins
-------------
A ``NewsItem.cropping`` is an ``ImageRatioField`` locked to
``NEWS_THUMBNAIL_SIZE`` (500x300 == 5:3). The admin Cropper.js widget lets an
editor pick a 5:3 crop box, stored as an "x1,y1,x2,y2" string. When a template
renders ``{% thumbnail news_item.image <W>x<H> box=news_item.cropping crop=True %}``
easy_thumbnails first applies that 5:3 box (via ``crop_corners``) and THEN, when
``<W>x<H>`` is a *different* aspect ratio, applies a SECOND center-crop to force
the target ratio -- silently trimming the top/bottom of the editor's chosen crop.

That second crop is invisible in the admin (the preview only ever shows the 5:3
box), so it shipped a head-clipping bug: the news *detail* page rendered at
750x350 (15:7) against a 5:3 crop and lopped off people's heads.

The durable fix is a rule: **every on-page crop render of a news image must use
the crop field's aspect ratio; only the pixel size may vary.** This test pins
that rule by scanning the templates, so a future size change to a mismatching
ratio fails here instead of silently re-cropping in production.

Intentional exceptions (a single stored crop box genuinely cannot be WYSIWYG at
these ratios) are listed in ``ALLOWED_EXCEPTIONS`` with the reason.
"""

import re
from pathlib import Path

from django.test import SimpleTestCase

from website.models.news import NEWS_THUMBNAIL_SIZE

# Directory holding this app's templates.
TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"

# Image sources whose renders must honor the news crop aspect ratio.
NEWS_IMAGE_SOURCES = {"news_item.image", "recent_news_item.image"}

# The crop editor / ImageRatioField aspect ratio (width / height).
NEWS_ASPECT = NEWS_THUMBNAIL_SIZE[0] / NEWS_THUMBNAIL_SIZE[1]

# Floating-point slack when comparing aspect ratios.
ASPECT_TOLERANCE = 0.01

# (width, height) render sizes that intentionally do NOT match the crop ratio,
# each with the reason it is exempt. A single stored 5:3 crop box cannot be
# WYSIWYG at these ratios, and that is acceptable here:
ALLOWED_EXCEPTIONS = {
    (1200, 630): (
        "Open Graph / social share card. 1200x630 (~1.91:1) is the platform "
        "standard; social sites re-crop to ~1.91:1 on their end regardless of "
        "what we send, so a single 5:3 crop box cannot be WYSIWYG for both the "
        "page and the social card. True fix would need a dedicated social crop."
    ),
    (50, 50): (
        "Round sidebar avatar chip. The CSS (.news-sidebar-image) forces a "
        "50x50 circle via object-fit:cover + border-radius:full, so the render "
        "is a deliberate decorative crop, not a WYSIWYG content image."
    ),
}

# Matches: {% thumbnail <src> <WxH> ...rest... %}
# <src> is the first positional arg (e.g. news_item.image); <size> is the
# WxH token, optionally single- or double-quoted; <rest> is everything up to %}.
THUMBNAIL_TAG_RE = re.compile(
    r"{%\s*thumbnail\s+(?P<src>[\w.]+)\s+"
    r"['\"]?(?P<w>\d+)x(?P<h>\d+)['\"]?"
    r"(?P<rest>[^%]*?)%}"
)


class NewsCropAspectRatioTests(SimpleTestCase):
    """Every cropped on-page render of a news image must match the crop ratio."""

    def _news_crop_renders(self):
        """
        Yield (template_path, w, h, tag) for every ``{% thumbnail %}`` tag in the
        app templates that renders a news image WITH a crop box and ``crop`` on.

        Only ``crop``-enabled renders can trigger the second center-crop; a
        non-crop render scales-to-fit and leaves the editor's box intact, so we
        deliberately skip those.
        """
        for template in TEMPLATES_DIR.rglob("*.html"):
            text = template.read_text(encoding="utf-8")
            for m in THUMBNAIL_TAG_RE.finditer(text):
                if m.group("src") not in NEWS_IMAGE_SOURCES:
                    continue
                rest = m.group("rest")
                if "box=" not in rest:
                    continue  # no crop box -> nothing to keep WYSIWYG
                if not re.search(r"\bcrop\b", rest):
                    continue  # scale-to-fit, no second crop
                yield (
                    template.relative_to(TEMPLATES_DIR),
                    int(m.group("w")),
                    int(m.group("h")),
                    m.group(0),
                )

    def test_scan_finds_the_detail_render(self):
        """Guard against the regex silently matching nothing (false pass)."""
        sizes = {(w, h) for _, w, h, _ in self._news_crop_renders()}
        self.assertIn(
            (750, 450),
            sizes,
            "Expected the news detail render (750x450) to be present. If the "
            "size changed, update this test AND confirm it still matches the "
            f"5:3 crop ratio. Found sizes: {sorted(sizes)}",
        )

    def test_on_page_news_renders_match_crop_aspect(self):
        mismatches = []
        for template, w, h, tag in self._news_crop_renders():
            if (w, h) in ALLOWED_EXCEPTIONS:
                continue
            aspect = w / h
            if abs(aspect - NEWS_ASPECT) > ASPECT_TOLERANCE:
                mismatches.append(
                    f"  {template}: {w}x{h} (ratio {aspect:.3f}) != crop ratio "
                    f"{NEWS_ASPECT:.3f}\n    {tag.strip()}"
                )

        self.assertFalse(
            mismatches,
            "These news image renders use a crop box but a target size whose "
            "aspect ratio differs from the crop editor's "
            f"({NEWS_THUMBNAIL_SIZE[0]}x{NEWS_THUMBNAIL_SIZE[1]} == "
            f"{NEWS_ASPECT:.3f}). easy_thumbnails will center-crop the editor's "
            "box a second time, trimming top/bottom (clipped heads). Fix the "
            "size to share the crop ratio, or add it to ALLOWED_EXCEPTIONS with "
            "a reason:\n" + "\n".join(mismatches),
        )
