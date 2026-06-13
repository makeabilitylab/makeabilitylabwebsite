from django.conf import settings
from django.shortcuts import render 
import logging

# This retrieves a Python logging instance (or creates it)
_logger = logging.getLogger(__name__)

def custom_404(request, exception):
    _logger.warning(f"custom_404: 404 error at {request.path}")
  
    context = {
        'requested_path': request.path,
        'exception': str(exception),  # Convert exception to string for rendering
        'navbar_white': True
    }

    # Use render() instead of HttpResponseNotFound
    # render() will handle the template processing
    # Pass status=404 to ensure the correct HTTP status code
    return render(request, 'website/404.html', context, status=404)