from django.db import models
from website.utils.fileutils import UniquePathAndRename
from .project import Project
from .sponsor import Sponsor
from image_cropping import ImageRatioField
from django.dispatch import receiver
from django.db.models.signals import pre_delete, post_save, m2m_changed, post_delete

class Banner(models.Model):
    FRONTPAGE = "FRONTPAGE"
    PEOPLE = "PEOPLE"
    PUBLICATIONS = "PUBLICATIONS"
    TALKS = "TALKS"
    PROJECTS = "PROJECTS"
    INDPROJECT = "INDPROJECT"
    NEWSLISTING = "NEWSLISTING"
    VIDEOS = "VIDEOS"
    PAGE_CHOICES = (
        (FRONTPAGE, "Front Page"),
        (NEWSLISTING, "News Listings"),
        (PEOPLE, "People"),
        (PUBLICATIONS, "Publications"),
        (TALKS, "Talks"),
        (PROJECTS, "Projects"),
        (INDPROJECT, "Ind_Project"),
        (VIDEOS, "Videos")
    )    
    page = models.CharField(max_length=50, choices=PAGE_CHOICES, default=FRONTPAGE)
    image = models.ImageField(blank=True, upload_to=UniquePathAndRename("banner", True), max_length=255)
    # This field is only needed if the banner has been assigned to a specific project. The field is used by project_ind to select project specific banners so we don't have to add each project to the PAGE_CHOICES dictionary.
    project = models.ForeignKey(Project, blank=True, null=True, on_delete=models.CASCADE)
    project.help_text = "If this banner is for a specific project, set the page to Ind_Project. You must also set this field to the desired project for your banner to be displayed on that projects page."
    # def image_preview(self):
    #     if self.image:
    #         return u'<img src="%s" style="width:100%%"/>' % self.image.url
    #     else:
    #         return '(Please upload an image)'
    # image_preview.short_description = 'Image Preview'
    # image_preview.allow_tags = True
    cropping = ImageRatioField('image', '2000x500', free_crop=True)
    image.help_text = 'You must select "Save and continue editing" at the bottom of the page after uploading a new image for cropping. Please note that since we are using a responsive design with fixed height banners, your selected image may appear differently on various screens.'
    title = models.CharField(max_length=50, blank=True, null=True)
    caption = models.CharField(max_length=1024, blank=True, null=True)
    alt_text = models.CharField(max_length=1024, blank=True, null=True)
    link = models.CharField(max_length=1024, blank=True, null=True)
    favorite = models.BooleanField(default=False)
    favorite.help_text = 'Check this box if this image should appear before other (non-favorite) banner images on the same page.'
    date_added = models.DateField(auto_now=True)

    def admin_thumbnail(self):
        if self.image:
            return u'<img src="%s" height="100"/>' % (self.image.url)
        else:
            return "No image found"

    admin_thumbnail.short_description = 'Thumbnail'
    admin_thumbnail.allow_tags = True

    def __str__(self):
        return "Title={} Page={} Project={}".format(self.title, self.page, self.project)


@receiver(pre_delete, sender=Banner)
def banner_delete(sender, instance, **kwargs):
    if instance.image:
        instance.image.delete(False)