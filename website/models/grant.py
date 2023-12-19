import os
from django.db import models
from website.models import Artifact

class Grant(Artifact):
    UPLOAD_DIR = 'grants/'
    THUMBNAIL_DIR = os.path.join(UPLOAD_DIR, 'images/')

    # A grant can have one sponsor. We make sure that sponsors cannot be deleted
    # if there are still grants that reference them.
    sponsor = models.ForeignKey('Sponsor', on_delete=models.PROTECT)
    sponsor.help_text = "Sponsor of the grant"

    end_date = models.DateField(null=True)
    end_date.help_text = "End date for this grant"

    funding_amount = models.IntegerField(null=True)
    funding_amount.help_text = "Amount of funding (in USD) for this grant"

    @property
    def start_date(self):
        return self.date

    def get_upload_dir(self, filename):
        return os.path.join(self.UPLOAD_DIR, filename)

    def get_upload_thumbnail_dir(self, filename):
        return os.path.join(self.THUMBNAIL_DIR, filename)