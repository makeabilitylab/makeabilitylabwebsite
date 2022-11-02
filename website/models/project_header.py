from django.db import models

import website.utils.ml_utils as ml_utils 

from .project import Project

# This class contains the image or video which will appear in the top description of each project. It functions as a 
# combination of Photo and Video, but is separated to make it simpler to have a specific video or photo as the projects header.
class ProjectHeader(models.Model):
    title = models.CharField(max_length=500)
    title.help_text = "These fields are used as the image in the about section. To add a banner to your page go to the banners table and assign banners to your project using the project field there. This field will accept both a video and an image. If both are provided the video will be used."
    caption = models.CharField(max_length=2000, blank=True, null=True)
    video_url = models.URLField(blank=True, null=True)
    image = models.ImageField(upload_to='projects/images/', blank=True, null=True, max_length=255)
    project = models.ForeignKey(Project, blank=True, null=True, on_delete=models.CASCADE)

    def has_video(self):
        """Returns true if the video_url is set"""
        if self.video_url:
            return True

        return False

    def get_video_embed(self):
        """Returns video embed code"""
        return ml_utils.get_video_embed(self.video_url)

    class Meta:
        verbose_name = "Project About Visual"