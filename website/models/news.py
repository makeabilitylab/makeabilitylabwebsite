from django.db import models
from django.dispatch import receiver
from django.db.models.signals import pre_delete, post_save, m2m_changed, post_delete

from django.urls import reverse_lazy
from django_prose_editor.fields import ProseEditorField
from website.utils.fileutils import UniquePathAndRename
from website.utils.upload_validators import validate_image_upload
from image_cropping import ImageRatioField

from django.utils.text import slugify

from datetime import date, datetime, timedelta

from .person import Person
from .project import Project

import random # for random news images

NEWS_THUMBNAIL_SIZE = (500, 300) # 15 : 9 aspect ratio

DEFAULT_NEWS_IMAGE_FILENAMES = ["MakeabilityLab-News2-DALLE3-Edits2-15x9.jpg",
                                "MakeabilityLab-News-DALLE3-Edits-15x9.jpg",
                                "MakeabilityLab-News-LaserCut3-DALLE3-15x9.jpg",
                                "MakeabilityLab-News-LaserCut4-DALLE3-Edits-15x9.jpg",
                                "MakeabilityLab-News-LaserCut-DALLE3-15x9.jpg"]
                                

class News(models.Model):

    @staticmethod  # use as decorator
    def get_thumbnail_size_as_str():
        return f"{NEWS_THUMBNAIL_SIZE[0]}x{NEWS_THUMBNAIL_SIZE[1]}"
    
    title = models.CharField(max_length=255)
    title.help_text = "The news title will be displayed on the landing page, news listing page, and the news item page."
    
    # A slug is a short label for something, containing only letters, numbers, underscores, or hyphrases. 
    # They’re generally used in URLs. We'll use the slug to let people visit our news pages by
    # the title of the news story rather than just the news.id
    slug = models.SlugField(null=True, unique=True, max_length=255)

    date = models.DateField(default=date.today) 
    author = models.ForeignKey(Person, null=True, on_delete=models.SET_NULL, related_name='authored_news')

    # Rich-text body, edited with django-prose-editor (issue #1269; replaced
    # CKEditor 4). `sanitize=True` cleans the HTML on save using an nh3 allowlist
    # derived from the enabled extensions below, so only markup the editor can
    # actually produce is stored. The Figure extension's `pickerUrl` wires the
    # "Browse…" image button to our staff-only upload view (see website/urls.py:
    # news_image_upload); reverse_lazy avoids a URL-resolution-at-import cycle.
    # Images are inserted without inline width/height so the responsive
    # `.news-item-content img` CSS governs sizing (news-item.css).
    content = ProseEditorField(
        extensions={
            "Bold": True, "Italic": True, "Underline": True, "Strike": True,
            "Subscript": True, "Superscript": True, "Code": True,
            "Heading": {"levels": [2, 3, 4]},
            "BulletList": True, "OrderedList": True, "ListItem": True,
            "Blockquote": True, "HorizontalRule": True,
            "TextAlign": True, "TextStyle": True,
            # "Edit HTML" source view for occasional manual tweaks. Adds nothing
            # to the sanitize allowlist, so source edits are still cleaned on
            # save (can't introduce disallowed tags like <script>).
            "HTML": True,
            "Link": {"enableTarget": True},
            # Figure wraps images in <figure>/<figcaption>; Image covers bare
            # <img> (all our legacy images) and Caption enables the captions.
            "Figure": {"pickerUrl": reverse_lazy("website:news_image_upload")},
            "Image": True, "Caption": True,
            # Document/Paragraph/Text/HardBreak/History/Menu are implied defaults
        },
        sanitize=True,
    )

    # Following the scheme of above thumbnails in other models
    image = models.ImageField(blank=True, upload_to=UniquePathAndRename("news", True), max_length=255, validators=[validate_image_upload])
    image.help_text = 'After choosing an image, crop it right here using the cropper below — no need to save first.'

    # We use the django-image-cropping ImageRatioField https://github.com/jonasundderwolf/django-image-cropping
    # that simply stores the boundaries of a cropped image. You must pass it the corresponding ImageField
    # and the desired size of the cropped image as arguments. The size passed in defines both the aspect ratio
    # and the minimum size for the final image
    cropping = ImageRatioField('image', get_thumbnail_size_as_str(), size_warning=True)

    # Caption and alt_text for the image
    caption = models.CharField(max_length=1024, blank=True, null=True)
    alt_text = models.CharField(max_length=1024, blank=True, null=True)

    # Set related projects to this news post
    project = models.ManyToManyField(Project, blank=True)
    project.help_text = "Manually add any projects that are related to this news item, which allows the news item to show on the appropriate project pages"
    people = models.ManyToManyField(Person, blank=True, related_name='related_news')
    people.help_text = "Manually add any people that are related to this news item, which allows the news item to show on the appropriate people pages"

    @property
    def default_news_image_filename(self):
        """This filename may change every time because it is random, pulled from DEFAULT_NEWS_IMAGE_FILENAMES"""
        if (not hasattr(self, '_default_news_image_filename') or not self._default_news_image_filename):
            self._default_news_image_filename = "website/img/news-thumbnails/" + random.choice(DEFAULT_NEWS_IMAGE_FILENAMES)
        return self._default_news_image_filename     

    def get_shortened_content(self, length=200, auto_add_ellipses=True):
        # add ellipses if we cut off the text
        append_str = ""
        if len(self.content) > length and auto_add_ellipses:
            append_str = "..."
        
        return self.content[:length] + append_str

    def short_date(self):
        month = self.date.strftime('%b')
        day = self.date.strftime('%d')
        year = self.date.strftime('%Y')
        return month + " " + day + ", " + year

    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
            num = 2
            # Exclude self.pk so an admin clearing the slug field on an
            # existing News item doesn't collide with its own row and
            # spuriously bump the counter on every re-save.
            while News.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f"{slugify(self.title)}-{num}"
                num += 1
        return super().save(*args, **kwargs)

    class Meta:
        # These names are used in the admin display, see https://docs.djangoproject.com/en/1.9/ref/models/options/#verbose-name
        ordering = ['-date', 'title']
        verbose_name = 'News Item'
        verbose_name_plural = 'News'


@receiver(pre_delete, sender=News)
def news_delete(sender, instance, **kwards):
    if instance.image:
        instance.image.delete(False)