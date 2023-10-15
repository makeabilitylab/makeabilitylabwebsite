from django.core.management.base import BaseCommand
from django.utils.text import slugify
from website.models import News

class Command(BaseCommand):
    help = 'Generate slugs for old news items. You should only need to run this command once'

    def handle(self, *args, **options):
        # Go through news items where there is no slug and generate a slug for them
        news_items_without_slug = News.objects.filter(slug__isnull=True) | News.objects.filter(slug='')
        for news_item_without_slug in news_items_without_slug:
            print(f"News id {news_item_without_slug.id}: Generating slug for news item '{news_item_without_slug.title}'")
            original_slug = slugify(news_item_without_slug.title)
            new_slug = original_slug
            num = 2

            # check to ensure that the slug is unique
            while News.objects.filter(slug=new_slug).exists():
                new_slug = f"{original_slug}-{num}"
                num += 1

            # save the slug
            print(f"News id {news_item_without_slug.id}: Saving slug '{new_slug}' for news item '{news_item_without_slug.title}'")
            news_item_without_slug.slug = new_slug
            news_item_without_slug.save()

        
