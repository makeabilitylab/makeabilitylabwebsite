from django.core.paginator import Paginator
from django.http import JsonResponse
from website.models import Project, Publication
from django.shortcuts import render, get_object_or_404

def ajax_example(request, format=None):
    page_number = request.GET.get('page', 1)  # Default to page 1 if no page parameter is provided
    list_type = request.GET.get('type')

    project_list = Project.objects.all().order_by('-start_date', 'name')
    publication_list = Publication.objects.all().order_by('-date', 'title')
    project_listing_size = 4
    pub_listing_size = 3

    proj_paginator = Paginator(project_list, project_listing_size)  # Show 4 projects per page
    proj_page = proj_paginator.get_page(page_number)

    pub_paginator = Paginator(publication_list, pub_listing_size)  # Show 3 publications per page
    pub_page = pub_paginator.get_page(page_number)

    if list_type == 'projects':
        return JsonResponse({"data": [f"{project.name}, {project.start_date}" for project in proj_page.object_list]})
    elif list_type == 'publications':
        return JsonResponse({"data": [str(pub) for pub in pub_page.object_list]})
   
    # Default case: show the first four projects and three publications
    return render(request, 'website/ajax_example.html', {
        'projects': proj_page,
        'publications': pub_page,
    })
