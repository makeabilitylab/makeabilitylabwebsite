from django.contrib import admin
from website.models import Poster
from website.models import Talk, Publication, PubType, TalkType
from website.admin import ArtifactAdmin
import logging
from website.admin.admin_site import ml_admin_site

# This retrieves a Python logging instance (or creates it)
_logger = logging.getLogger(__name__)

@admin.register(Poster, site=ml_admin_site)
class PosterAdmin(ArtifactAdmin):

    # search_fields are used for auto-complete, see:
    #   https://docs.djangoproject.com/en/3.0/ref/contrib/admin/#django.contrib.admin.ModelAdmin.autocomplete_fields
    search_fields = ['title', 'date']

    def get_changeform_initial_data(self, request):
        """
        Pre-fills the poster form with data from a related publication.
        
        When adding a new poster from a publication's admin page, this method
        reads the publication_id from the URL query parameters and uses that
        publication's data to pre-populate matching fields in the poster form.
        
        Args:
            request: The HTTP request object containing GET parameters.
            
        Returns:
            dict: Initial form data, potentially pre-filled from a publication.
        """
        _logger.debug(f"request is {request} and request.GET is {request.GET}")

        initial = super().get_changeform_initial_data(request)
        publication_id = request.GET.get('publication_id')
        
        if publication_id:
            try:
                publication = Publication.objects.get(id=publication_id)
                initial.update({
                    'title': publication.title,
                    'date': publication.date,
                    'forum_name': publication.forum_name,
                    'forum_url': publication.forum_url,
                    'location': publication.location,
                })
                
                # For ManyToManyFields, set the initial data as a list of IDs
                initial['authors'] = publication.authors.all().values_list('id', flat=True)
                initial['projects'] = publication.projects.all().values_list('id', flat=True)
                initial['project_umbrellas'] = publication.project_umbrellas.all().values_list('id', flat=True)
                initial['keywords'] = publication.keywords.all().values_list('id', flat=True)
                
            except Publication.DoesNotExist:
                pass
                
        return initial