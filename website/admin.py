from django.contrib import admin

from .models import Person, Publication, Position, Talk, Project, Poster, Keyword, News, Banner, Video, Project_header, Photo, Project_umbrella, Project_Role, Sponsor
from website.admin_list_filters import CurrentMemberListFilter, PositionListFilter, PubVenueTypeListFilter, PubVenueListFilter

from django.http import HttpResponse
from datetime import datetime
from django.template import loader
from django.template import RequestContext

from django.shortcuts import redirect

from django import forms

import urllib

import bibtexparser

from image_cropping import ImageCroppingMixin

class BannerAdmin(ImageCroppingMixin, admin.ModelAdmin):
    fieldsets = [
        (None, {'fields': ["page", "title", "caption", "alt_text", "link", "favorite", "project"]}),
        # ('Image', {'fields': ["image", "image_preview"]})
        ('Image', {'fields': ["image", "cropping"]})
    ]
    list_display = ('__str__', 'admin_thumbnail')
    # readonly_fields = ["image_preview"]


class PositionInline(admin.StackedInline):
    model = Position

    # This specifies that the Inline is linked to the main owner of the position rather than any of the advisor roles.
    fk_name = "person"

    # This specifies that the field appears only once (by default)
    extra = 0

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        print("PositionInline.formfield_for_foreignkey: db_field: {} db_field.name {} request: {}".format(db_field, db_field.name, request))

        if db_field.name == "advisor" or db_field.name == "co_advisor":
            # Filters advisors to professors and sorts by first name
            # Based on: http://stackoverflow.com/a/30627555
            professor_ids = [person.id for person in Person.objects.all() if person.is_professor()]
            filtered_persons = Person.objects.filter(id__in=professor_ids).order_by('first_name')
            print(filtered_persons)
            kwargs["queryset"] = filtered_persons
        elif db_field.name == "grad_mentor":
            # Filters grad mentor list to current grad students (either member or collaborator)
            grad_ids = [person.id for person in Person.objects.all() if person.is_grad_student() and (person.is_current_member() or person.is_current_collaborator())]
            filtered_persons = Person.objects.filter(id__in=grad_ids).order_by('first_name')
            print(filtered_persons)
            kwargs["queryset"] = filtered_persons

        return super(PositionInline, self).formfield_for_foreignkey(db_field, request, **kwargs)
    
class ProjectRoleInline(admin.StackedInline):
    model = Project_Role
    extra = 0

class ProjectHeaderInline(ImageCroppingMixin, admin.StackedInline):
    model = Project_header
    extra = 0

# Uses format as per https://github.com/jonasundderwolf/django-image-cropping to add cropping to the admin page
class NewsAdmin(ImageCroppingMixin, admin.ModelAdmin):
    # Filters authors only to current members and sorts by firstname
    # Based on: http://stackoverflow.com/a/30627555
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # print("NewsAdmin.formfield_for_foreignkey: db_field: {} db_field.name {} request: {}".format(db_field, db_field.name, request))
        if db_field.name == "author":
            current_member_ids = [person.id for person in Person.objects.all() if person.is_current_member()]
            filtered_persons = Person.objects.filter(id__in=current_member_ids).order_by('first_name')
            print(filtered_persons)
            kwargs["queryset"] = filtered_persons
        return super(NewsAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)


class PhotoAdmin(ImageCroppingMixin, admin.ModelAdmin):
    list_display = ('__str__', 'admin_thumbnail')

class ProjectAdmin(ImageCroppingMixin, admin.ModelAdmin):
    inlines = [ProjectHeaderInline]

class PersonAdmin(ImageCroppingMixin, admin.ModelAdmin):

    # inlines allow us to edit models on the same page as a parent model
    # see: https://docs.djangoproject.com/en/1.11/ref/contrib/admin/#inlinemodeladmin-objects
    inlines = [PositionInline, ProjectRoleInline]

    # The list display lets us control what is shown in the default persons table at Home > Website > People
    # info on displaying multiple entries comes from http://stackoverflow.com/questions/9164610/custom-columns-using-django-admin
    list_display = ('get_full_name', 'get_current_title', 'get_current_role', 'is_active', 'get_start_date', 'get_end_date', 'get_time_in_current_position', 'get_total_time_as_member')

    #TODO setup filter here that has diff categories (like active members, past, etc.):
    #https://www.elements.nl/2015/03/16/getting-the-most-out-of-django-admin-filters/
    #related to: https://github.com/jonfroehlich/makeabilitylabwebsite/issues/238
    list_filter = (CurrentMemberListFilter, PositionListFilter)
    # prepopulated_fields = {'url_name':('first_name', 'last_name',)}

class VideoAdmin(admin.ModelAdmin):
    # The list display lets us control what is shown in the default persons table at Home > Website > Videos
    # info on displaying multiple entries comes from http://stackoverflow.com/questions/9164610/custom-columns-using-django-admin
    list_display = ('title', 'date', 'caption', 'project')

    # default the sort order in table to descending order by date
    ordering = ('-date',)

class TalkAdmin(admin.ModelAdmin):
    # Filters speakers only to current members and collaborators and sorts by first name
    # Based on: https://stackoverflow.com/a/17457828
    def formfield_for_manytomany(self, db_field, request, **kwargs):
        print("TalkAdmin.formfield_for_manytomany: db_field: {} db_field.name {} request: {}".format(db_field, db_field.name, request))
        if db_field.name == "speakers":
            current_member_and_collab_ids = [person.id for person in Person.objects.all() if person.is_current_member()]
            filtered_persons = Person.objects.filter(id__in=current_member_and_collab_ids).order_by('first_name')
            print(filtered_persons)
            kwargs["queryset"] = filtered_persons
        return super(TalkAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)


class PublicationAdmin(admin.ModelAdmin):
    fieldsets = [
        (None,                      {'fields': ['title', 'authors', 'date']}),
        ('Files',                   {'fields': ['pdf_file']}),
        ('Pub Venue information',   {'fields': ['pub_venue_type', 'book_title', 'book_title_short', 'geo_location', 'total_papers_submitted', 'total_papers_accepted']}),
        ('Archival Info',           {'fields': ['official_url', 'extended_abstract', 'peer_reviewed', 'award' ]}),
        ('Video Info',              {'fields': ['video']}),
        ('Page Info',               {'fields': ['num_pages', 'page_num_start', 'page_num_end']}),
        ('Talk Info',               {'fields': ['talk']}),
        ('Project Info',            {'fields': ['projects', 'project_umbrellas']}),
        ('Keyword Info',            {'fields': ['keywords']}),
    ]
    list_display = ('title', 'book_title_short', 'date')

    # default the sort order in table to descending order by date
    ordering = ('-date',)

    list_filter = (PubVenueTypeListFilter, PubVenueListFilter)

    # Uncomment this function to enable auto-entry from bibtex
    # The following code is based in part on a hint by this Stackoverflow post: http://stackoverflow.com/a/4952370
    # See: http://stackoverflow.com/a/10041463 for overiding admin forms
    # def add_view(self, request, **kwargs):

    #     if request.method == 'POST':
    #         # Stage 1 form submitted, parse data and redirect to with data in url to get Django to auto-fill in form
    #         extra_context = {}

    #         extra_context['test_var'] = 'In stage 2!'

    #         bibtex_str = request.POST['bibtex_textarea']
    #         if 'submitbibtex_button' in request.POST and len(bibtex_str) > 0:

    #             bib_database = bibtexparser.loads(bibtex_str)
    #             bib_entry = bib_database.entries[0]
    #             # str_items = ""
    #             # for key in bib_entry:
    #             #     str_items = str_items + "{}={}&".format(key, bib_entry[key])
    #             #
    #             # raw_url = '/admin/website/publication/add/?{}'.format(str_items)
    #             # prepared_url = urllib.parse.urlencode(raw_url)
    #             #return redirect()

    #             # TODO: The problem is that passing values in the url only works if those values are already existing
    #             # django entries. So, for example, if you pass in a bibtex that has a new, never-before-seen author
    #             # then we need to create that Author database entry first. I also cannot actually get one-to-many fields
    #             # like authors to actually pass correctly by value in the url.
    #             params = urllib.parse.urlencode(bib_entry)
    #             redirect_url = '/admin/website/publication/add/?{}'.format(params)
    #             return redirect(redirect_url)
    #             #return redirect('/admin/website/publication/add/?title="test"')
    #         else:
    #             return redirect('/admin/website/publication/add/?title=')

    #     elif not request.GET:

    #         opts = self.model._meta
    #         app_label = opts.app_label

    #         template = loader.get_template('admin/website/publication/bibtex_form.html')
    #         context = RequestContext(request)

    #         # because bibtex_form.thml extends the 'admin/change_form.html' template, we need to add in some variables
    #         # that change_form.html requires. See: http://stackoverflow.com/questions/28777376/problems-extend-change-form-html-in-django-admin
    #         # and specifically the answer: http://stackoverflow.com/a/28777461
    #         context.push(
    #                 {"test_var": "in stage 1",
    #                  'opts': opts,
    #                  'app_label': app_label,
    #                  'change': False,
    #                  'is_popup': False,
    #                  'save_as': False,
    #                  'has_delete_permission': False,
    #                  'has_add_permission': False,
    #                  'has_change_permission': False}
    #         )
    #         return HttpResponse(template.render(context))
    #     elif request.GET:
    #         extra_context = {}
    #         extra_context['test_var'] = 'In stage 1'
    #         return super(PublicationAdmin, self).add_view(request, extra_context=extra_context, **kwargs)

admin.site.register(Person, PersonAdmin)
admin.site.register(Publication, PublicationAdmin)
admin.site.register(Talk, TalkAdmin)
admin.site.register(Project, ProjectAdmin)
admin.site.register(Poster)
admin.site.register(Keyword)
admin.site.register(News, NewsAdmin)
admin.site.register(Banner, BannerAdmin)
admin.site.register(Video, VideoAdmin)
admin.site.register(Photo, PhotoAdmin)
admin.site.register(Project_umbrella)
admin.site.register(Sponsor)
admin.site.register(Position)