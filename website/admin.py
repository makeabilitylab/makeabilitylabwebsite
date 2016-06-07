from django.contrib import admin

from .models import Person, Publication, Position, Talk, Project, Poster, Keyword, News, Banner

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
        (None, {'fields': ["page", "title", "caption", "alt_text"]}),
        # ('Image', {'fields': ["image", "image_preview"]})
        ('Image', {'fields': ["image", "cropping"]})
    ]
    # readonly_fields = ["image_preview"]


#class ChoiceInline(admin.StackedInline):
class RoleInline(admin.StackedInline):
    model = Position
    extra = 1

class PersonAdmin(ImageCroppingMixin, admin.ModelAdmin):
    inlines = [RoleInline]

class PublicationAdmin(admin.ModelAdmin):
    fieldsets = [
        (None,                      {'fields': ['title', 'authors', 'date']}),
        ('Files',                   {'fields': ['pdf_file']}),
        ('Pub Venue information',   {'fields': ['pub_venue_type', 'book_title', 'book_title_short', 'geo_location', 'total_papers_submitted', 'total_papers_accepted']}),
        ('Archival Info',           {'fields': ['official_url', 'extended_abstract', 'peer_reviewed', 'award' ]}),
        ('Video Info',              {'fields': ['video_url', 'video_preview_url']}),
        ('Page Info',               {'fields': ['num_pages', 'page_num_start', 'page_num_end']}),
        ('Talk Info',               {'fields': ['talk']}),
        ('Project Info',            {'fields': ['projects']}),
        ('Keyword Info',            {'fields': ['keywords']}),
    ]
    list_display = ('title', 'book_title_short')

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
# admin.site.register(Member)
admin.site.register(Publication, PublicationAdmin)
admin.site.register(Talk)
admin.site.register(Project)
admin.site.register(Poster)
admin.site.register(Keyword)
admin.site.register(News)
admin.site.register(Banner, BannerAdmin)