import time

# Note: I could not get this code to work correctly. When activated in settings.py,
# it would *almost* work but then the content of the page never seemed to stop loading
# I couldn't figure this out so I just commented out the middleware in settings.py

class RenderTimingMiddleware:
    """
    Middleware for measuring the time it takes to render a response.
    This middleware replaces a special string in the response content
    with the actual render time.
    """

    def __init__(self, get_response):
        """
        Initialize the middleware.

        Args:
            get_response: A callable that takes a request and returns a response.
                          This will be the actual view that gets called with the request.
        """
        self.get_response = get_response

    def __call__(self, request):
        """
        Process the request and response.

        This method is called for each request. It calls the view with the request,
        measures the time it takes to get the response, and replaces a special string
        in the response content with the actual render time.

        Args:
            request: The request that was made.

        Returns:
            The response generated by the view.
        """
        # Code to be executed for each request before
        # the view (and later middleware) are called.
        start_time = time.perf_counter()

        response = self.get_response(request)

        # Code to be executed for each request/response after
        # the view is called.
        end_time = time.perf_counter()
        render_time = end_time - start_time
        render_time_str = f"{render_time:0.4f} seconds"

        # Only replace in text/html responses
        if response['Content-Type'] == 'text/html; charset=utf-8':
            if 'DEBUG_INSERT_RENDER_TIMING' in response.content.decode():
                response.content = response.content.replace(
                    'DEBUG_INSERT_RENDER_TIMING'.encode(), 
                    render_time_str.encode(), 
                    1
                )
        print("*****render time*******", render_time_str)
        return response