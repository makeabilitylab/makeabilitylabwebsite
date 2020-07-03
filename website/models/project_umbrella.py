from django.db import models
from .keyword import Keyword

# TODO: Argh, need to change all multi-world class names to CapWords convention, 
# see official docs: https://www.python.org/dev/peps/pep-0008/#id41
class Project_umbrella(models.Model):
    name = models.CharField(max_length=255)
    # Short name is used for urls, and should be name.lower().replace(" ", "")
    short_name = models.CharField(max_length=255)
    short_name.help_text = "This should be the same as your name but lower case with no spaces. It is used in the url of the project"
    keywords = models.ManyToManyField(Keyword, blank=True, null=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Project Umbrella"