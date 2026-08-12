import os
from django.db import models
from website.models import Artifact

from django.db.models.signals import pre_save # to handle when sponsors change
from django.dispatch import receiver # to handle when sponsors change

import logging # for logging

# This retrieves a Python logging instance (or creates it)
_logger = logging.getLogger(__name__)

class Grant(Artifact):
    UPLOAD_DIR = 'grants/'
    THUMBNAIL_DIR = os.path.join(UPLOAD_DIR, 'images/')

    # A grant can have one sponsor. We make sure that sponsors cannot be deleted
    # if there are still grants that reference them.
    sponsor = models.ForeignKey('Sponsor', on_delete=models.PROTECT)
    sponsor.help_text = "Sponsor of the grant"

    # In Django, to make a field optional in the admin form, you need to set blank=True in addition 
    # to null=True in your model field. The null=True allows the database to store a NULL value 
    # for the field, while blank=True allows the field to be blank in forms, including the admin form.
    end_date = models.DateField(blank=True, null=True)
    end_date.help_text = "End date for this grant"

    funding_amount = models.IntegerField(null=True)
    funding_amount.help_text = "Amount of funding (in USD) for this grant"

    # verbose_name (rather than only an admin form label) so the "sponsor's vs
    # UW's" distinction also shows on the *read-only* change form Editors see:
    # Django's readonly rendering reads the model's verbose_name and ignores
    # ModelAdmin form label overrides (django.contrib.admin.utils.label_for_field).
    grant_id = models.CharField(verbose_name="Sponsor grant ID",
                                max_length=255, null=True, blank=True)
    grant_id.help_text = "The sponsor's own ID for this grant (e.g., <a href='https://www.nsf.gov/awardsearch/showAward?AWD_ID=1302338'>1302338</a>). This one is public."

    # --- UW internal tracking (#1448) ---------------------------------------
    # Careful: `grant_id` above is the *sponsor's* award ID (the NSF number). It
    # is public information and is serialized by the REST API. The three fields
    # below are UW/Workday's own administrative codes for the same award. They
    # are INTERNAL: deliberately absent from GrantSerializer's field allowlist
    # (see website/api/serializers.py) and never rendered on a public page.
    # Non-superusers can *view* them in the admin — that's the point, sponsored-
    # programs staff ask for the worktag constantly — but not the funding data
    # or proposal files alongside them (see GrantAdmin.get_fieldsets).

    uw_grant_id = models.CharField(verbose_name="UW Grant ID (worktag)",
                                   max_length=255, null=True, blank=True)
    uw_grant_id.help_text = ("UW's internal grant worktag, e.g. GR012345. If the award "
                             "spans several worktags, list them comma-separated. "
                             "<b>Internal only</b> — never shown publicly or in the REST API.")

    uw_award_number = models.CharField(verbose_name="UW Award number",
                                       max_length=255, null=True, blank=True)
    uw_award_number.help_text = "UW's award number for this grant, e.g. AWD-00012345. Internal only."

    uw_award_name = models.CharField(verbose_name="UW Award name",
                                     max_length=512, null=True, blank=True)
    uw_award_name.help_text = ("The award name as UW records it, which is often not the "
                               "title above. Internal only.")

    @property
    def start_date(self):
        return self.date
    
    @property
    def grant_url(self):
        return self.forum_url
    
    @grant_url.setter
    def grant_url(self, value):
        self.forum_url = value

    def get_upload_dir(self, filename):
        return os.path.join(self.UPLOAD_DIR, filename)

    def get_upload_thumbnail_dir(self, filename):
        return os.path.join(self.THUMBNAIL_DIR, filename)
    
    def save(self, *args, **kwargs):
        if self.forum_name is None:
            _logger.debug(f"Grant {self.title} has no forum_name, setting to sponsor")

            if self.sponsor.short_name is not None:
                self.forum_name = self.sponsor.short_name
            elif self.sponsor.name is not None:
                self.forum_name = self.sponsor.name

            _logger.debug(f"Grant {self.title} now has forum_name {self.forum_name}.")

        super(Grant, self).save(*args, **kwargs)
    
@receiver(pre_save, sender=Grant)
def check_sponsor_change(sender, instance, **kwargs):
    if instance.id is not None:  # this is not a new object
        old_grant = Grant.objects.get(id=instance.id)
        if old_grant.sponsor != instance.sponsor:
            _logger.debug(f"Grant {instance.title} changed sponsor from {old_grant.sponsor} to {instance.sponsor}.")

            if instance.sponsor.short_name is not None:
                instance.forum_name = instance.sponsor.short_name
            elif instance.sponsor.name is not None:
                instance.forum_name = instance.sponsor.name

            _logger.debug(f"Grant {instance.title} now has forum_name {instance.forum_name}.")