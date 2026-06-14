import os
from django.db import models
from website.models import Artifact

class Poster(Artifact):
    UPLOAD_DIR = 'posters/'
    THUMBNAIL_DIR = os.path.join(UPLOAD_DIR, 'images/')

    external_slides_url = models.URLField(blank=True, null=True)
    external_slides_url.help_text = (
        "Optional link to the source design (e.g., Figma, Canva, Illustrator "
        "online). <b>Strongly recommended</b>: also upload an archival raw "
        "file above (a .fig from Figma, .ai from Illustrator, etc.) &mdash; "
        "cloud links break when students graduate or revoke access."
    )

    def get_upload_dir(self, filename):
        return os.path.join(self.UPLOAD_DIR, filename)

    def get_upload_thumbnail_dir(self, filename):
        return os.path.join(self.THUMBNAIL_DIR, filename)