from django.shortcuts import render

def ajax_example(request, format=None):
    return render(request, 'website/ajax_example.html')