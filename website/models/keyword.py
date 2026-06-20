import re

from django.db import models

class Keyword(models.Model):
    keyword = models.CharField(max_length=255)

    def save(self, *args, **kwargs):
        """Normalize whitespace before saving so casual variants can't create
        near-duplicate tags (#1352). Trims the ends and collapses internal runs
        of whitespace to a single space, so "Speech ", " Speech", and
        "Speech  recognition" can't coexist with their clean forms.

        This is the partial, no-migration ward (layer 1): it catches every
        creation path, including the inline "add keyword" widget on Publication/
        Project forms. Case-insensitive uniqueness (e.g. blocking "Speech" vs
        "speech") is a separate DB constraint deferred until existing dupes are
        merged — casing is intentionally preserved here (VR, HCI, iOS).
        """
        if self.keyword:
            self.keyword = re.sub(r'\s+', ' ', self.keyword).strip()
        super().save(*args, **kwargs)

    def get_project_count(self):
        """Returns the number of projects that use keyword"""
        return self.project_set.count()
    
    get_project_count.short_description = 'Projects'
    
    def get_publication_count(self):
        """Returns the number of publications that use this keyword"""
        return self.publication_set.count()

    get_publication_count.short_description = 'Publications'

    def __str__(self):
        return self.keyword