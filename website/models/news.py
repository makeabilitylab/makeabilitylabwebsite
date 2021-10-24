from django.db import models
from django.dispatch import receiver
from django.db.models.signals import pre_delete, post_save, m2m_changed, post_delete

from ckeditor_uploader.fields import RichTextUploadingField
from website.utils.fileutils import UniquePathAndRename
from image_cropping import ImageRatioField

from datetime import date, datetime, timedelta

from .person import Person
from .project import Project

class News(models.Model):
    title = models.CharField(max_length=255)
    #date = models.DateTimeField(default=timezone.now)
    date = models.DateField(default=date.today)  # check this line, might be diff
    author = models.ForeignKey(Person, null=True, on_delete=models.SET_NULL)
    content = RichTextUploadingField(config_name='default')
    # Following the scheme of above thumbnails in other models
    image = models.ImageField(blank=True, upload_to=UniquePathAndRename("news", True), max_length=255)
    image.help_text = 'You must select "Save and continue editing" at the bottom of the page after uploading a new image for cropping. Please note that since we are using a responsive design with fixed height banners, your selected image may appear differently on various screens.'

    # Copied from person model
    # LS: Added image cropping to fixed ratio
    # See https://github.com/jonasundderwolf/django-image-cropping
    # size is "width x height"
    # TODO: update with desired aspect ratio and maximum resolution
    cropping = ImageRatioField('image', '245x245', size_warning=True)

    # Optional caption and alt_text for the image
    caption = models.CharField(max_length=1024, blank=True, null=True)
    alt_text = models.CharField(max_length=1024, blank=True, null=True)

    project = models.ManyToManyField(Project, blank=True, null=True)

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

    class Meta:
        # These names are used in the admin display, see https://docs.djangoproject.com/en/1.9/ref/models/options/#verbose-name
        ordering = ['-date', 'title']
        verbose_name = 'News Item'
        verbose_name_plural = 'News'


@receiver(pre_delete, sender=News)
def news_delete(sender, instance, **kwards):
    if instance.image:
        instance.image.delete(False)