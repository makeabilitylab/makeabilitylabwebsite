from django.http import HttpResponse, Http404
from django.shortcuts import redirect
from django.core.exceptions import ObjectDoesNotExist
from website.models import Publication
import os
import glob
import difflib
import logging

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
        closest_filename = get_closest_filename_from_database(filename)
        _logger.debug(f"Closest match to {filename} in database is {closest_filename}")
        if closest_filename:
            closest_filename = os.path.basename(closest_filename)
            redirect_path = f'/media/publications/{closest_filename}'
            _logger.debug(f"Redirecting to {redirect_path}")
            return redirect(redirect_path, filename=closest_filename)
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
    return get_closest_filename(query_filename, all_filenames, cutoff)


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
    return get_closest_filename(query_filename, all_filenames, cutoff)
    
def get_closest_filename(query_filename, all_filenames, cutoff=0.8):
    """
    Finds the closest matching filename from a list of filenames based on a query filename.
    Args:
        query_filename (str): The filename to search for.
        all_filenames (list of str): A list of filenames to search within.
        cutoff (float, optional): A float in the range [0, 1] that specifies the minimum similarity 
                                  ratio for a match to be considered. Defaults to 0.8.
    Returns:
        str or None: The closest matching filename if a match is found, otherwise None.
    """

    # Get the closest matching filename using difflib
    # We specify n=3 to get the top 3 closest matches and a cutoff value of 0.8
    # The cutoff value determines the minimum similarity ratio for a match to be considered
    closest_match_array = difflib.get_close_matches(query_filename, all_filenames, n=3, cutoff=cutoff)

    _logger.debug(f"Closest match array for {query_filename} is {closest_match_array}")

    closest_match = None
    if closest_match_array:
        closest_match = closest_match_array[0]

    return closest_match