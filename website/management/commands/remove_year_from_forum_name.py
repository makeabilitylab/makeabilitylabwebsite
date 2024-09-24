from django.core.management.base import BaseCommand
from website.models import Publication
import website.utils.ml_utils as ml_utils
import website.utils.timeutils as ml_timeutils
from django.conf import settings
import os
import logging

# This retrieves a Python logging instance (or creates it)
_logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "This is a one time use command to update forum names for publications"

    def handle(self, *args, **options):
        _logger.debug("Running remove_year_from_forum_name.py to remove the year from forum names. Should only be run once")
        
        # Loop through all publications and clean up the forum name
        changed_forum_names = []
        for pub in Publication.objects.all():
            old_forum_name = pub.forum_name
            new_forum_name = ml_utils.clean_forum_name(old_forum_name)  

            if old_forum_name != new_forum_name:  
                pub.forum_name = new_forum_name  
                pub.save(update_fields=['forum_name'])

                _logger.debug(f"The forum name for {pub} has been renamed from {old_forum_name} to {pub.forum_name}")
                changed_forum_names.append((old_forum_name, pub))
        
        # Print out stats about the changes
        _logger.debug(f"Checked {Publication.objects.all().count()} publications, changed {len(changed_forum_names)} forum name(s).")
        for old_name, pub in changed_forum_names:
            _logger.debug(f"{pub.title}: changed {old_name} to {pub.forum_name}")

        _logger.debug("Completed remove_year_from_forum_name.py")

            