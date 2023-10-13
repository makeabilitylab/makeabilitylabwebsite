from django.db import models
from .keyword import Keyword

class ProjectUmbrella(models.Model):
    name = models.CharField(max_length=255)
    
    short_name = models.CharField(max_length=255)
    short_name.help_text = "Used for some UI elements, e.g., the project gallery page"
    
    keywords = models.ManyToManyField(Keyword, blank=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Project Umbrella"