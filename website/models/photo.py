from django.db import models

from image_cropping import ImageRatioField

from .project import Project

class Photo(models.Model):
    picture = models.ImageField(upload_to='projects/images/', max_length=255)
    caption = models.CharField(max_length=255, blank=True, null=True)
    alt_text = models.CharField(max_length=255, blank=True, null=True)
    project = models.ForeignKey(Project, blank=True, null=True, on_delete=models.SET_NULL)
    picture.help_text = 'You must select "Save and continue editing" at the bottom of the page after uploading a new image for cropping. Please note that since we are using a responsive design with fixed height banners, your selected image may appear differently on various screens.'

    # Copied from person model
    # LS: Added image cropping to fixed ratio
    # See https://github.com/jonasundderwolf/django-image-cropping
    # size is "width x height"
    # TODO: update with desired aspect ratio and maximum resolution
    cropping = ImageRatioField('picture', '368x245', size_warning=True)

    def admin_thumbnail(self):
        return u'<img src="%s" height="100"/>' % (self.picture.url)

    admin_thumbnail.short_description = 'Thumbnail'
    admin_thumbnail.allow_tags = True

    def __str__(self):
        return self.caption