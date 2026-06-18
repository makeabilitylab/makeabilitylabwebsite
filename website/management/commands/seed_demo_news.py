"""
Local-dev / CI helper: seed a few demo news items so the news listing
(``/news/``) and a news detail page render with real content.

Run inside the website container (or in CI):

    python manage.py seed_demo_news

Idempotent — deletes any prior demo news (title starting with "Demo News")
and recreates from scratch, so it's safe to re-run. Pairs with
``seed_demo_projects``: together they populate enough content for the Pa11y
accessibility sweep (#1278 item 6) to scan real pages rather than empty ones.
If demo people exist (from ``seed_demo_projects``), the first one is set as the
author so the byline path renders too.

News.save() derives the slug from the title, so the detail URLs are stable:
"Demo News One" -> /news/demo-news-one/.

This file lives in management/commands/ so Django auto-discovers it, but it's
explicitly a dev/test tool — don't wire it into docker-entrypoint.sh.
"""

from datetime import date

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Seed a few demo news items (for local visual testing and the Pa11y CI sweep)."

    _TITLES = ["Demo News One", "Demo News Two", "Demo News Three"]

    def handle(self, *args, **opts):
        from website.models import News, Person

        wiped = News.objects.filter(title__startswith="Demo News").count()
        if wiped:
            self.stdout.write(self.style.WARNING(f"Removing {wiped} prior demo news item(s)."))
            News.objects.filter(title__startswith="Demo News").delete()

        # Reuse a demo author if seed_demo_projects has run; otherwise authorless
        # (News.author is nullable) — both paths should render.
        author = Person.objects.filter(first_name="Demo").order_by("last_name").first()

        self.stdout.write(self.style.NOTICE("Creating demo news items…"))
        for i, title in enumerate(self._TITLES):
            news = News.objects.create(
                title=title,
                content=(
                    f"<p>This is demo news item #{i + 1}, created for local visual "
                    f"testing and the automated accessibility (Pa11y) sweep.</p>"
                ),
                date=date(2024, 1, i + 1),
                author=author,
            )
            self.stdout.write(f"  ✓ /news/{news.slug}/")

        self.stdout.write(self.style.SUCCESS("Done."))
