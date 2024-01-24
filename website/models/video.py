from django.db import models

from datetime import date, datetime, timedelta

import website.utils.ml_utils as ml_utils 

class Video(models.Model):
    video_url = models.URLField(blank=True, null=True)
    video_preview_url = models.URLField(blank=True, null=True)
    title = models.CharField(max_length=255)
    caption = models.CharField(max_length=255, blank=True, null=True)
    date = models.DateField(null=True)

    projects = models.ManyToManyField('Project', blank=True, null=True, related_name='videos')
    #project = models.ForeignKey('Project', blank=True, null=True, on_delete=models.SET_NULL)

    def get_video_host_str(self):
        if 'youtu.be' in self.video_url or 'youtube.com' in self.video_url:
            return 'YouTube'
        elif 'vimeo' in self.video_url:
            return 'Vimeo'
        else:
            return 'Video'

    def has_publication(self):
        """Check if video has an associate publication using a reverse query. See:
           https://stackoverflow.com/a/40743258"""
        return hasattr(self, 'publication')

    def get_embed(self):
        """Given self.video_url, returns the correctly formatted video embed url for YouTube and Vimeo"""
        return ml_utils.get_video_embed(self.video_url)

    def get_age_in_ms(self):
        """Gets the age of this video in milliseconds (as an integer)"""
        age_td = datetime.now().date() - self.date # calculate age as a timedelta object
        age_in_ms = age_td.total_seconds() * 1000 # conver to milliseconds
        return int(age_in_ms)

    def __str__(self):
        return "{}, {}, {}".format(self.title, self.get_video_host_str(), self.date)