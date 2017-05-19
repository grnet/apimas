import json
import re
from django.http import HttpResponse
from apimas.errors import ConflictError
from apimas.adapters.actions import Request


HTTP_REGEX = re.compile(r'^HTTP_+$')
CONTENT_TYPE_REGEX = re.compile(r'^CONTENT_TYPE$')
CONTENT_LENGTH_REGEX = re.compile(r'^CONTENT_LENGTH$')


class DjangoWrapper(object):
    """
    A class which is actually a wrapper of the apimas actions. It is
    responsible for:
        * Conversion of the django request into apimas.
        * Execution of the action pipelines.
        * Conversion of the apimas response into django.

    It is initialized with a dict of actions which are mapped to the
    same url pattern but they use a different HTTP method.
    """
    def __init__(self, actions):
        self.actions = actions

    def get_headers(self, request):
        """
        Get headers from Django Request object.

        All HTTP headers begin with 'HTTP_' except for content_type and
        content_length.


        See: http://bit.ly/2mRWjk9

        Args:
            request: Django request object.

        Returns:
            dict: Dictionary with the headers of the request.
        """
        request_headers = {}
        regex_patterns = [HTTP_REGEX, CONTENT_TYPE_REGEX, CONTENT_LENGTH_REGEX]
        for header in request.META.iterkeys():
            if any(regex.match(header) for regex in regex_patterns):
                request_headers[header] = request.META[header]
        return request_headers

    def get_body(self, request):
        """
        Get the body from Django request object.

        The body of the request can be JSON serializable based on its content
        type. Otherwise, we get the content of request from the `request.POST`
        attribute.

        Args:
            request: Django request object.

        Returns:
            dict: Dictionary with body of the request.
        """
        if not request.body:
            return {}
        content_type = self.get_content_type(request)
        if content_type == 'application/json':
            body_unicode = request.body.decode('utf-8')
            return json.loads(body_unicode)
        else:
            # `request.POST` is a multival dict so we create
            # a python native dict.
            return {k: v for k, v in request.POST.iteritems()}

    def get_files(self, request):
        """ Get files of the Django request object. """
        # `request.FILES` is a multival dict so we create a new one.
        return {k: v for k, v in request.FILES.iteritems()}

    def get_query_params(self, request):
        """ Get query parameters of the Django request object. """
        return request.GET

    def get_content_type(self, request):
        """
        Get the content type of the request based on the corresponding HTTP
        header.
        """
        return request.META.get('CONTENT_TYPE')

    def create_native_response(self, response):
        """
        Creates a Django `HttpResponse` object response using the apimas
        response object. The created object is actually used by the backend
        to serve the response to the client.

        Args:
            response: APIMAS response object.

        Returns:
            Django native response.
        """
        if response.get_native() is not None:
            raise ConflictError('Native Response object already exists')
        content = response.content
        content_type = response.kwargs.get('content_type')
        if content_type == 'application/json':
            content = json.dumps(content)
        status_code = response.kwargs.get('status_code')
        return HttpResponse(content=content, content_type=content_type,
                            status=status_code)

    def _get_apimas_request(self, request, **kwargs):
        """
        Creates an APIMAS request object based on the initial django request.
        """
        params = self.get_query_params(request)
        body = self.get_body(request)
        headers = self.get_headers(request)
        files = self.get_files(request)
        # Merge data and the files of the request.
        data = dict(body, **files)
        kwargs.update({
            'params': params,
            'files': files,
            'headers': headers,
        })
        return Request(content=data, native=request, **kwargs)

    def execute_action(self, action, request, **kwargs):
        apimas_request = self._get_apimas_request(request, **kwargs)
        apimas_response = action.process_request(apimas_request)
        action.process_response(apimas_response)
        django_response = self.create_native_response(apimas_response)
        return django_response

    def __call__(self, request, **kwargs):
        """
        Django function-based views.

        The actual view which is mapped with a url pattern.
        """
        action = self.actions.get(request.method)
        return self.execute_action(action, request, **kwargs)
