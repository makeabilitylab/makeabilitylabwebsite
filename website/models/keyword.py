from django.db import models

class Keyword(models.Model):
    keyword = models.CharField(max_length=255)

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