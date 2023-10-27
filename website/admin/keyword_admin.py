from django.contrib import admin
from django.db.models import Count
from website.models import Keyword

@admin.register(Keyword)
class KeywordAdmin(admin.ModelAdmin):
    list_display = ['keyword', 'project_count', 'publication_count']

    def change_view(self, request, object_id, form_url='', extra_context=None):
        """Add projects and publications to the context. We then use this extra data in
        the change_form.html template to display the projects and publications that use this keyword.
        This change_form.html template is found in website/admin/templates/admin/website/keyword/change_form.html
        """
        extra_context = extra_context or {}
        keyword = Keyword.objects.get(pk=object_id)
        extra_context['projects'] = keyword.project_set.all().order_by('-start_date')
        extra_context['publications'] = keyword.publication_set.all().order_by('-date')
        return super().change_view(
            request, object_id, form_url, extra_context=extra_context,
        )
    
    def get_queryset(self, request):
        """Annotate queryset with project and publication counts"""
        queryset = super().get_queryset(request)

        # When you have multiple annotations, Django’s Count treats each instance of the related model 
        # (Project and Publication in this case) as separate instances, hence you get the same count for both.
        # To get distinct counts for Project and Publication, you need to pass distinct=True to the Count function.
        queryset = queryset.annotate(_project_count=Count("project", distinct=True), 
                                     _publication_count=Count("publication", distinct=True))
        return queryset

    def project_count(self, obj):
        """Return the number of projects that use keyword"""
        return obj._project_count
    
    project_count.admin_order_field = '_project_count'

    def publication_count(self, obj):
        """Return the number of publications that use this keyword"""
        return obj._publication_count
    
    publication_count.admin_order_field = '_publication_count'
    