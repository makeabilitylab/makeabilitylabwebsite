"""
One-shot, idempotent normalizer that strips inline image dimensions from News
content (issue #1269).

Under CKEditor 4, inserted images carried inline ``style="width:...;height:..."``
(and sometimes ``width``/``height`` attributes). Those inline dimensions
*override* the site's responsive rule (``.news-item-content img { max-width:
100%; height: auto }`` in news-item.css), which is why each image historically
had to be hand-edited in "source" to ``width:100%`` with its height erased.

django-prose-editor drops ``style`` on ``<img>`` when it sanitizes on save, so
*new* and *re-saved* posts are already clean. This command applies the same
cleanup to *legacy* rows that haven't been re-saved, so every news image becomes
responsive immediately rather than lazily. It only removes width/height (from
both the ``style`` attribute and the ``width``/``height`` attributes) and leaves
all other markup untouched.

It is idempotent (a second run changes nothing) and writes via ``queryset
.update()`` to avoid re-running model save/validation. It is wired into
docker-entrypoint.sh alongside the other idempotent backfills, which is the only
way to touch prod data (no shell/manage.py access on the servers).
"""

import re

from django.core.management.base import BaseCommand

from website.models import News

# A whole <img ...> tag.
_IMG_TAG_RE = re.compile(r"<img\b[^>]*>", re.IGNORECASE)
# A width/height *attribute* on the tag: width="300", height='2', width=300.
_DIM_ATTR_RE = re.compile(
    r'\s+(?:width|height)\s*=\s*(?:"[^"]*"|\'[^\']*\'|[^\s>]+)', re.IGNORECASE
)
# A width/height *declaration* inside a style value: "width: 100%;".
_DIM_DECL_RE = re.compile(r"\s*(?:width|height)\s*:\s*[^;]*;?", re.IGNORECASE)
# The style attribute and its quoted value.
_STYLE_ATTR_RE = re.compile(
    r'(\s+style\s*=\s*)(?:"([^"]*)"|\'([^\']*)\')', re.IGNORECASE
)


def _clean_style(match):
    """Drop width/height declarations from one style="..." attribute."""
    prefix = match.group(1)
    double = match.group(2)
    quote = '"' if double is not None else "'"
    value = double if double is not None else match.group(3)
    new_value = _DIM_DECL_RE.sub("", value).strip().strip(";").strip()
    if not new_value:
        return ""  # nothing left -> drop the style attribute entirely
    return f"{prefix}{quote}{new_value}{quote}"


def _normalize_img_tag(tag):
    tag = _DIM_ATTR_RE.sub("", tag)
    tag = _STYLE_ATTR_RE.sub(_clean_style, tag)
    return tag


def normalize_image_dimensions(html):
    """
    Strip inline width/height (style declarations + width/height attributes)
    from every ``<img>`` tag in ``html``. All other markup is preserved.

    >>> normalize_image_dimensions('<img src="a.jpg" style="width:100%">')
    '<img src="a.jpg">'
    """
    if not html or "<img" not in html.lower():
        return html
    return _IMG_TAG_RE.sub(lambda m: _normalize_img_tag(m.group(0)), html)


class Command(BaseCommand):
    help = (
        "Strip inline width/height from <img> tags in News.content so images "
        "rely on the responsive .news-item-content img CSS. Idempotent; safe to "
        "run repeatedly (issue #1269)."
    )

    def handle(self, *args, **options):
        changed = 0
        for news in News.objects.all():
            original = news.content or ""
            cleaned = normalize_image_dimensions(original)
            if cleaned != original:
                News.objects.filter(pk=news.pk).update(content=cleaned)
                changed += 1
                self.stdout.write(f"News id {news.pk}: normalized image dimensions")
        self.stdout.write(
            self.style.SUCCESS(
                f"normalize_news_image_styles: updated {changed} news item(s)."
            )
        )
