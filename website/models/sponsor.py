from django.db import models
import os

class Sponsor(models.Model):
    UPLOAD_DIR = 'sponsors/'
    ICON_DIR = os.path.join(UPLOAD_DIR, 'images/')

    name = models.CharField(max_length=255)
    name.help_text = "Full name of the sponsor (e.g., National Science Foundation)"

    short_name = models.CharField(max_length=255, null=True)
    short_name.help_text = "Short name for the sponsor (e.g., NSF)"

    icon = models.ImageField(upload_to=ICON_DIR, blank=True, null=True, max_length=255)
    icon.help_text = "Icon for the sponsor (e.g., NSF logo)"

    url = models.URLField(blank=True, null=True)
    url.help_text = "URL for the sponsor (e.g., https://www.nsf.gov)"

    def __str__(self):
        return self.name