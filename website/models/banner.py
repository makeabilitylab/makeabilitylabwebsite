from django.db import models
from django.dispatch import receiver
from django.db.models.signals import pre_delete, post_save, m2m_changed, post_delete

from website.utils.fileutils import UniquePathAndRename
from image_cropping import ImageRatioField

from .project import Project
from .sponsor import Sponsor

import os # for joining paths

class Banner(models.Model):
    UPLOAD_DIR = 'banner/' # relative path
    VIDEO_UPLOAD_DIR = os.path.join(UPLOAD_DIR, "videos")

    landing_page = models.BooleanField(default=False)
    landing_page.help_text = 'Check this box if this banner should appear on the landing page.'

    image = models.ImageField(blank=True, upload_to=UniquePathAndRename(UPLOAD_DIR, True), max_length=255)
    cropping = ImageRatioField('image', '1600x500', free_crop=False)
    image.help_text = 'You must select "Save and continue editing" at the bottom of the page after uploading a new image for cropping.\
                      Please note that since we are using a responsive design with fixed height banners, your selected image may appear\
                      differently on various screens.'
    
    video = models.FileField(upload_to=UniquePathAndRename(VIDEO_UPLOAD_DIR, True), blank=True, null=True)
    video.help_text = "Add in a background video. If both a video and image are specified, the video is prioritized. The image is fallback."
    
    alt_text = models.CharField(max_length=1024, blank=True, null=True)
    alt_text.help_text = "Please set the alt text for the banner"

    # You can optionally decide to link a banner to a project so it will show on its project page
    project = models.ForeignKey(Project, blank=True, null=True, on_delete=models.CASCADE)
    project.help_text = "If relevant, set the project associated with this banner"
    
    title = models.CharField(max_length=50, blank=True, null=True)
    title.help_text = "Titles are bold overlays on top of the banner"

    caption = models.CharField(max_length=1024, blank=True, null=True)
    caption.help_text = "If specified, captions are shown under the title"

    link = models.CharField(max_length=1024, blank=True, null=True)
    link.help_text = "Specify a url if you want the banner to be hyperlinked, which will activate on a click"
    
    favorite = models.BooleanField(default=False)
    favorite.help_text = 'Check this box if this banner should appear before other (non-favorite) banner images on the same page.'
    
    date_added = models.DateField(auto_now=True)
    date_added.help_text = "When there are many banners specified for a page, we prioritize more recently added banners"

    def admin_thumbnail(self):
        if self.image:
            return u'<img src="%s" height="100"/>' % (self.image.url)
        else:
            return "No image found"

    admin_thumbnail.short_description = 'Thumbnail'
    admin_thumbnail.allow_tags = True

    def __str__(self):
        return "Title={} Project={} LandingPage={}".format(self.title, self.project, self.landing_page)


@receiver(pre_delete, sender=Banner)
def banner_delete(sender, instance, **kwargs):
    # delete image file (if it exists)
    if instance.image:
        instance.image.delete(False)

    # delete video file (if it exists)
    if instance.video:
        instance.video.delete(False)