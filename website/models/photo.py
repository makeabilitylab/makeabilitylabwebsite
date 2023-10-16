from django.db import models
from django.utils.safestring import mark_safe
from image_cropping import ImageRatioField

from .project import Project

DEFAULT_CROPPING_SIZE = (600, 400)

class Photo(models.Model):

    @staticmethod  # use as decorator
    def get_cropping_size_as_str():
        return f"{DEFAULT_CROPPING_SIZE[0]}x{DEFAULT_CROPPING_SIZE[1]}"

    picture = models.ImageField(upload_to='projects/images/', max_length=255)

    # TODO: force both caption and alt_text to be non-null and non-blank
    # This requires a migration so need to talk with Matt/Jason in IT about it.
    caption = models.CharField(max_length=255, blank=True, null=True)
    alt_text = models.CharField(max_length=255, blank=True, null=True)

    # on_delete=models.SET_NULL means that when the related Project object is deleted, 
    # the project attribute of the related Photo objects will be set to NULL. This is only 
    # possible if null=True is set for the field, which it is. So, if a Project is deleted, it won’t 
    # delete the Photo objects associated with it but instead, it will disassociate them by 
    # setting their project attribute to NULL. This can be useful if you want to keep the Photo 
    # objects even if the associated Project no longer exists. 
    # Comment generated with help from chat.bing.com
    # See also: https://docs.djangoproject.com/en/4.2/ref/models/fields/#django.db.models.ForeignKey.on_delete
    project = models.ForeignKey(Project, blank=True, null=True, on_delete=models.SET_NULL)
    picture.help_text = 'To crop this image, you must select "Save and continue editing" at the bottom of the page after uploading'
    
    # We use the django-image-cropping ImageRatioField https://github.com/jonasundderwolf/django-image-cropping
    # that simply stores the boundaries of a cropped image. You must pass it the corresponding ImageField
    # and the desired size of the cropped image as arguments. The size passed in defines both the aspect ratio
    # and the minimum size for the final image
    cropping = ImageRatioField('picture', get_cropping_size_as_str(), size_warning=True)

    def admin_thumbnail(self):
        """Returns an HTML snippet to render the thumbnail image in the admin site"""
        return mark_safe(f"<img src='{self.picture.url}' height='50'/>") 

    admin_thumbnail.short_description = 'Thumbnail'

    def get_resolution_as_str(self):
        return f"{self.picture.width}x{self.picture.height}"
    
    get_resolution_as_str.short_description = 'Resolution'

    def __str__(self):
        if self.caption:
            return self.caption
        else:
            return "No description"