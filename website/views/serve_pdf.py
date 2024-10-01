from django.http import HttpResponse, Http404
from django.shortcuts import redirect
from django.core.exceptions import ObjectDoesNotExist
from website.models import Publication
import os
import glob
import difflib
import logging
import website.utils.ml_utils as ml_utils

# This retrieves a Python logging instance (or creates it)
_logger = logging.getLogger(__name__)

def serve_pdf(request, filename):
    """
    This function serves a PDF file based on the requested filename.
    It finds the closest matching filename in the publications directory

    Args:
        request (HttpRequest): The Django HTTP request object containing information
                              about the user's request.
        filename (str): The filename of the requested PDF file.
    """
    _logger.debug(f"serve_pdf with request={request} and filename={filename}")

    try:
        artifact = Publication.objects.get(pdf_file__icontains=filename)
        _logger.debug(f"Found exact match for {filename} in database")
      
        # PDF found in database, serve it
        response = HttpResponse(artifact.pdf_file.read(), content_type='application/pdf')
        response['Content-Disposition'] = f'inline;filename={artifact.pdf_file.name}'
        return response
    except ObjectDoesNotExist:
        # If the artifact does not exist, try to find the closest matching filename in pub database
        _logger.debug(f"{filename} not found in database, looking for closest match in pub database")
        closest_filename = get_closest_filename_from_database(filename, 0.7)
        _logger.debug(f"Closest match to {filename} in database is {closest_filename}")
        if closest_filename:
            closest_filename = os.path.basename(closest_filename)
            redirect_path = f'/media/publications/{closest_filename}'
            _logger.debug(f"Redirecting to {redirect_path}")
            return redirect(redirect_path)
        else:
            error_message = f"The PDF {filename} was not found."
            if closest_filename:
                error_message += f" The closest match was {closest_filename}."
            raise Http404(error_message)
    
def get_closest_filename_from_database(query_filename, cutoff=0.8):
    """
    Retrieves the closest matching filename from the database based on the provided query filename.
    Args:
        query_filename (str): The filename to search for in the database.
        cutoff (float, optional): The similarity threshold for matching filenames. Defaults to 0.8.
    Returns:
        str: The closest matching filename from the database.
    """
    
    all_filenames = Publication.objects.values_list('pdf_file', flat=True)
    return ml_utils.get_closest_match(query_filename, all_filenames, cutoff)


def get_closest_filename_from_filesystem(query_filename, dir_path, cutoff=0.8):
    """
    Finds the closest matching filename to the given query filename within a specified directory.
    Args:
        query_filename (str): The filename to search for.
        dir_path (str): The path to the directory containing the files.
        cutoff (float, optional): The similarity threshold for matching filenames. Defaults to 0.8.
    Returns:
        str: The filename from the directory that most closely matches the query filename.
    """
    
    # Get all filenames in the directory
    all_filenames = glob.glob(dir_path + "/*.pdf")    
    return ml_utils.get_closest_match(query_filename, all_filenames, cutoff)