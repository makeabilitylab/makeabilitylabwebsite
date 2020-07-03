from django.db import models

from .project import Project

# This class contains the image or video which will appear in the top description of each project. It functions as a combination of Photo and Video, but is separated to make it simpler to have a specific video or photo as the projects header.
# TODO: I want to rename Project_header to ProjectHeader
# but it looks like this is a bit of a pain, see: https://stackoverflow.com/questions/25091130/django-migration-strategy-for-renaming-a-model-and-relationship-fields
class Project_header(models.Model):
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
        return get_video_embed(self.video_url)

    class Meta:
        verbose_name = "Project About Visual"

def get_video_embed(video_url):
    """Returns proper embed code for a video url"""

    if 'youtu.be' in video_url or 'youtube.com' in video_url:
        # https://youtu.be/i0IDbHGir-8 or https://www.youtube.com/watch?v=i0IDbHGir-8

        base_url = "https://youtube.com/embed"
        unique_url = video_url[video_url.find("/", 9):]

        # See https://developers.google.com/youtube/youtube_player_demo for details on parameterizing YouTube video
        return base_url + unique_url + "?showinfo=0&iv_load_policy=3"
    elif 'vimeo' in video_url:
        # https://player.vimeo.com/video/164630179
        vimeo_video_id = video_url.rsplit('/', 1)[-1]
        return "https://player.vimeo.com/video/" + vimeo_video_id
    else:
        return "unknown video service for '{}'".format(video_url)