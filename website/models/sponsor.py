from django.db import models
from image_cropping import ImageRatioField
import os

SPONSOR_THUMBNAIL_SIZE = (245, 245)

class Sponsor(models.Model):
    UPLOAD_DIR = 'sponsors/'
    ICON_DIR = os.path.join(UPLOAD_DIR, 'images/')

    @staticmethod  # use as decorator
    def get_thumbnail_size_as_str():
        return f"{SPONSOR_THUMBNAIL_SIZE[0]}x{SPONSOR_THUMBNAIL_SIZE[1]}"

    name = models.CharField(max_length=255)
    name.help_text = "Full name of the sponsor (e.g., National Science Foundation)"

    short_name = models.CharField(max_length=255, null=True)
    short_name.help_text = "Short name for the sponsor (e.g., NSF)"

    icon = models.ImageField(upload_to=ICON_DIR, blank=True, null=True, max_length=255)
    icon.help_text = "Icon for the sponsor (e.g., NSF logo)"

    alt_text = models.CharField(max_length=1024, blank=True, null=True)
    alt_text.help_text = "Please set the alt text for the icon"
    
    # For thumbnail generation, we use the django-image-cropping ImageRatioField https://github.com/jonasundderwolf/django-image-cropping
    # that simply stores the boundaries of a cropped image. You must pass it the corresponding ImageField
    # and the desired size of the cropped image as arguments. The size passed in defines both the aspect ratio
    # and the minimum size for the final image
    icon_cropping = ImageRatioField('icon', get_thumbnail_size_as_str(), size_warning=True)

    url = models.URLField(blank=True, null=True)
    url.help_text = "URL for the sponsor (e.g., https://www.nsf.gov)"

    def __str__(self):
        return self.name
    
    def get_icon_alt_text(self):
        if not self.alt_text:
            return "This is the icon for the sponsor " + self.name
        else:
            return self.thumbnail_alt_text