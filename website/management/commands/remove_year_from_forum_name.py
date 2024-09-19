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
    help = "This is a one time use command to update poster filenames"

    def handle(self, *args, **options):
        _logger.debug("Running remove_year_from_forum_name.py to remove the year from forum names. Should only be run once")
        
        # Loop through all publications and clean up the forum name
        for pub in Publication.objects.all():
            old_forum_name = pub.forum_name
            new_forum_name = ml_utils.clean_forum_name(old_forum_name)  

            if old_forum_name != new_forum_name:  
                pub.forum_name = new_forum_name  
                pub.save(update_fields=['forum_name'])

                _logger.debug(f"The forum name for {pub} has been renamed from {old_forum_name} to {pub.forum_name}")