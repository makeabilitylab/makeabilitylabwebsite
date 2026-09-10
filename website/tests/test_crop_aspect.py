"""
Regression test for the image crop aspect-ratio contract.

Bug this pins
-------------
Every ``ImageRatioField`` on a model (``News.cropping``, ``Project.cropping``,
``Person.cropping``, ...) locks the admin Cropper.js widget to one aspect ratio
and stores the editor's chosen rectangle as an "x1,y1,x2,y2" string. When a
template renders ``{% thumbnail obj.image <W>x<H> box=obj.cropping crop=True %}``
easy_thumbnails first applies that box (via ``crop_corners``) and THEN, when
``<W>x<H>`` is a *different* aspect ratio, applies a SECOND center-crop to force
the target ratio -- silently trimming the edges of the editor's chosen crop.

That second crop is invisible in the admin (the preview only ever shows the
crop box), so it ships as a head-clipping bug: the news *detail* page rendered
at 750x350 (15:7) against a 5:3 crop, and the related-projects sidebar rendered
at 160x90 (16:9) against the 5:3 ``Project.cropping`` (#1416).

The durable fix is a rule: **every crop-enabled render must use its crop
field's aspect ratio; only the pixel size may vary.** This test pins that rule
by scanning the templates -- for every crop field, not just news -- so a future
size change to a mismatching ratio fails here instead of silently re-cropping
in production. ``CropProcessorTests`` pins the pixel-level behavior the rule
exists to prevent.

Intentional exceptions (a single stored crop box genuinely cannot be WYSIWYG at
these ratios) are listed in ``ALLOWED_EXCEPTIONS`` with the reason.
"""

import re
from pathlib import Path

from django.test import SimpleTestCase
from easy_thumbnails.processors import scale_and_crop
from PIL import Image

from image_cropping.fields import max_cropping
from image_cropping.thumbnail_processors import crop_corners
from website.models import Award, Banner, News, Person, Photo, Project, Sponsor

# Directory holding this app's templates.
TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"

# Every ``box=`` expression the templates pass to {% thumbnail %}, mapped to the
# (model, ImageRatioField) that defines its aspect ratio. The ratio is read off
# the field itself, so a change to a model's crop size can never leave this test
# asserting a stale number.
CROP_BOX_FIELDS = {
    "news_item.cropping": (News, "cropping"),
    "recent_news_item.cropping": (News, "cropping"),
    "project.cropping": (Project, "cropping"),
    "related_project.cropping": (Project, "cropping"),
    "person.cropping": (Person, "cropping"),
    "author.cropping": (Person, "cropping"),
    "member.person.cropping": (Person, "cropping"),
    "member.person.easter_egg_crop": (Person, "easter_egg_crop"),
    "banner.cropping": (Banner, "cropping"),
    "image.cropping": (Photo, "cropping"),
    "award.badge_cropping": (Award, "badge_cropping"),
    "sponsor.icon_cropping": (Sponsor, "icon_cropping"),
}

# Floating-point slack when comparing aspect ratios.
ASPECT_TOLERANCE = 0.01

# (width, height) render sizes that intentionally do NOT match the crop ratio,
# each with the reason it is exempt. A single stored crop box cannot be WYSIWYG
# at these ratios, and that is acceptable here:
ALLOWED_EXCEPTIONS = {
    (1200, 630): (
        "Open Graph / social share card. 1200x630 (~1.91:1) is the platform "
        "standard; social sites re-crop to ~1.91:1 on their end regardless of "
        "what we send, so a single crop box cannot be WYSIWYG for both the "
        "page and the social card. True fix would need a dedicated social crop "
        "(#1417)."
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

# Matches the crop box argument inside a {% thumbnail %} tag: box=project.cropping
BOX_ARG_RE = re.compile(r"\bbox=(?P<box>[\w.]+)")


def _crop_aspect(model, field_name):
    """Aspect ratio (width / height) of a model's ImageRatioField."""
    field = model._meta.get_field(field_name)
    return field.width / field.height


class CropAspectRatioTests(SimpleTestCase):
    """Every cropped on-page render must match its crop field's aspect ratio."""

    def _crop_renders(self):
        """
        Yield (template_path, box_expr, w, h, tag) for every ``{% thumbnail %}``
        tag in the app templates that renders WITH a crop box and ``crop`` on.

        Only ``crop``-enabled renders can trigger the second center-crop; a
        non-crop render scales-to-fit and leaves the editor's box intact, so we
        deliberately skip those.
        """
        for template in TEMPLATES_DIR.rglob("*.html"):
            text = template.read_text(encoding="utf-8")
            for m in THUMBNAIL_TAG_RE.finditer(text):
                rest = m.group("rest")
                box = BOX_ARG_RE.search(rest)
                if not box:
                    continue  # no crop box -> nothing to keep WYSIWYG
                if not re.search(r"\bcrop\b", rest):
                    continue  # scale-to-fit, no second crop
                yield (
                    template.relative_to(TEMPLATES_DIR),
                    box.group("box"),
                    int(m.group("w")),
                    int(m.group("h")),
                    m.group(0),
                )

    def test_scan_finds_the_known_renders(self):
        """Guard against the regex silently matching nothing (false pass)."""
        sizes = {(w, h) for _, _, w, h, _ in self._crop_renders()}
        for expected in [(750, 450), (160, 96)]:
            self.assertIn(
                expected,
                sizes,
                f"Expected a {expected[0]}x{expected[1]} crop render (the news "
                "detail image and the related-projects sidebar thumbnail). If a "
                "size changed, update this test AND confirm the new size still "
                f"matches its crop ratio. Found sizes: {sorted(sizes)}",
            )

    def test_every_crop_box_is_registered(self):
        """A new crop render must be added to CROP_BOX_FIELDS, not skipped."""
        unknown = sorted(
            {
                f"  {template}: box={box}"
                for template, box, _, _, _ in self._crop_renders()
                if box not in CROP_BOX_FIELDS
            }
        )
        self.assertFalse(
            unknown,
            "These templates crop against a box this test doesn't know about, "
            "so their aspect ratio is unchecked. Map each one to its model and "
            "ImageRatioField in CROP_BOX_FIELDS:\n" + "\n".join(unknown),
        )

    def test_crop_renders_match_their_crop_aspect(self):
        mismatches = []
        for template, box, w, h, tag in self._crop_renders():
            if (w, h) in ALLOWED_EXCEPTIONS or box not in CROP_BOX_FIELDS:
                continue
            model, field_name = CROP_BOX_FIELDS[box]
            crop_aspect = _crop_aspect(model, field_name)
            aspect = w / h
            if abs(aspect - crop_aspect) > ASPECT_TOLERANCE:
                field = model._meta.get_field(field_name)
                mismatches.append(
                    f"  {template}: {w}x{h} (ratio {aspect:.3f}) != "
                    f"{model.__name__}.{field_name} ratio {crop_aspect:.3f} "
                    f"({field.width}x{field.height})\n    {tag.strip()}"
                )

        self.assertFalse(
            mismatches,
            "These renders use a crop box but a target size whose aspect ratio "
            "differs from the crop editor's. easy_thumbnails will center-crop "
            "the editor's box a second time, trimming the edges (clipped "
            "heads). Fix the size to share the crop ratio, or add it to "
            "ALLOWED_EXCEPTIONS with a reason:\n" + "\n".join(mismatches),
        )


class CropProcessorTests(SimpleTestCase):
    """
    Pin the pixel-level behavior the aspect rule exists to prevent.

    Renders through the real processor chain (``crop_corners`` then
    easy_thumbnails' ``scale_and_crop``, exactly as THUMBNAIL_PROCESSORS wires
    them) with the top and bottom edges of the editor's box painted, and checks
    whether those edges survive into the thumbnail.
    """

    ORIGINAL_SIZE = (1000, 800)
    EDGE_BAND = 10
    RED = (255, 0, 0)
    BLUE = (0, 0, 255)

    def _render_project_crop(self, size):
        field = Project._meta.get_field("cropping")
        box = max_cropping(field.width, field.height, *self.ORIGINAL_SIZE)

        source = Image.new("RGB", self.ORIGINAL_SIZE, "white")
        band = (self.ORIGINAL_SIZE[0], self.EDGE_BAND)
        source.paste(Image.new("RGB", band, self.RED), (0, box[1]))
        source.paste(Image.new("RGB", band, self.BLUE), (0, box[3] - self.EDGE_BAND))

        boxed = crop_corners(source, box=",".join(str(v) for v in box))
        return scale_and_crop(boxed, size, crop=True, upscale=True)

    def _edge_pixels(self, image):
        """Top-centre and bottom-centre pixels of a rendered thumbnail."""
        middle = image.size[0] // 2
        return image.getpixel((middle, 0)), image.getpixel((middle, image.size[1] - 1))

    def test_matching_aspect_preserves_the_whole_crop_box(self):
        """160x96 shares Project.cropping's 5:3, so both box edges survive."""
        top, bottom = self._edge_pixels(self._render_project_crop((160, 96)))

        self.assertLess(top[1], 80, f"top of the crop box was trimmed: {top}")
        self.assertGreater(top[0], 200, f"top of the crop box was trimmed: {top}")
        self.assertLess(bottom[1], 80, f"bottom of the crop box was trimmed: {bottom}")
        self.assertGreater(bottom[2], 200, f"bottom of the crop box was trimmed: {bottom}")

    def test_mismatched_aspect_trims_the_crop_box(self):
        """160x90 (16:9) re-crops the 5:3 box, losing both painted edges."""
        top, bottom = self._edge_pixels(self._render_project_crop((160, 90)))

        self.assertGreater(
            top[1],
            200,
            "a 16:9 render of a 5:3 crop box should have center-cropped the "
            f"editor's top edge away, but it survived: {top}",
        )
        self.assertGreater(
            bottom[1],
            200,
            "a 16:9 render of a 5:3 crop box should have center-cropped the "
            f"editor's bottom edge away, but it survived: {bottom}",
        )
