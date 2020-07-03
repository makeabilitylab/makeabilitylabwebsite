from django.db import models

class Sponsor(models.Model):
    name = models.CharField(max_length=255)
    icon = models.ImageField(upload_to='projects/sponsors/', blank=True, null=True, max_length=255)
    url = models.URLField(blank=True, null=True)

    def __str__(self):
        return self.name